// figma-to-godot exporter: Figma Plugin API -> "figma-to-godot/0.1" design JSON.
//
// STATUS: written against the official Plugin API typings (plugin-typings,
// dynamic-page safe: only the *Async variants). NOT yet run against a live
// Figma file. Treat the first run as a test and compare with the frames.
//
// Run it any of these ways:
//   1. Claude + the Figma MCP: pass this file's body to `use_figma` (load the
//      figma-use skill first). The returned JSON is the design file.
//   2. Paste into a development plugin's code.ts and call exportDesign().
//
// Exports the current selection (frames), or every top-level frame on the page.

const SCHEMA = "figma-to-godot/0.1";

const hex = (c, a = 1) => {
  const h = (v) => Math.round(v * 255).toString(16).padStart(2, "0").toUpperCase();
  return "#" + h(c.r) + h(c.g) + h(c.b) + (a < 1 ? h(a) : "");
};

async function resolveVariable(id, modeId, depth = 0) {
  // Follow alias chains down to a literal COLOR / FLOAT value.
  const v = await figma.variables.getVariableByIdAsync(id);
  if (!v || depth > 8) return null;
  let val = v.valuesByMode[modeId];
  if (val === undefined) val = Object.values(v.valuesByMode)[0];
  if (val && val.type === "VARIABLE_ALIAS") return resolveVariable(val.id, modeId, depth + 1);
  return { variable: v, value: val };
}

async function exportCollections() {
  const out = [];
  const cols = await figma.variables.getLocalVariableCollectionsAsync();
  for (const col of cols) {
    const modes = col.modes.map((m) => m.name);
    const variables = [];
    for (const id of col.variableIds) {
      const v = await figma.variables.getVariableByIdAsync(id);
      if (!v || (v.resolvedType !== "COLOR" && v.resolvedType !== "FLOAT")) continue;
      const values = {};
      for (const m of col.modes) {
        const r = await resolveVariable(id, m.modeId);
        if (!r || r.value === undefined) continue;
        values[m.name] = v.resolvedType === "COLOR" ? hex(r.value, r.value.a ?? 1) : r.value;
      }
      variables.push({ name: v.name, type: v.resolvedType, values });
    }
    out.push({ name: col.name, modes, variables });
  }
  return { collections: out, defaultMode: out[0] ? out[0].modes[0] : "Default" };
}

async function paintToFill(paints) {
  const p = (paints || []).find((x) => x.visible !== false);
  if (!p) return null;
  if (p.type === "SOLID") {
    const ref = { color: hex(p.color, p.opacity ?? 1) };
    const bound = p.boundVariables && p.boundVariables.color;
    if (bound) {
      const v = await figma.variables.getVariableByIdAsync(bound.id);
      if (v) ref.var = v.name;
    }
    return ref;
  }
  if (p.type.startsWith("GRADIENT") && p.gradientStops.length) {
    const s = p.gradientStops[0];
    return { color: hex(s.color, s.color.a ?? 1), gradient: true };
  }
  return null; // IMAGE fills are handled as assets by the caller
}

const NUMERIC = (n, k) => (typeof n[k] === "number" ? n[k] : undefined);

async function exportNode(node, parent) {
  if (node.visible === false) return null;
  const t = node.type;
  const o = {
    type: t,
    name: node.name,
    x: NUMERIC(node, "x") ?? 0,
    y: NUMERIC(node, "y") ?? 0,
    width: Math.round(node.width),
    height: Math.round(node.height),
  };
  const godotType = node.getPluginData && node.getPluginData("godotType");
  if (godotType) o.godotType = godotType;

  if ("layoutSizingHorizontal" in node) {
    o.sizing = { h: node.layoutSizingHorizontal, v: node.layoutSizingVertical };
  }
  if (node.rotation) o.rotation = node.rotation;
  const fx = (node.effects || []).filter((e) => e.visible !== false).map((e) => e.type);
  if (fx.length) o.effects = fx;

  if ("fills" in node && t !== "TEXT") {
    const imageFill = (node.fills || []).find((f) => f.type === "IMAGE" && f.visible !== false);
    if (imageFill) {
      o.type = "IMAGE";
      o.asset = node.name.replace(/[^A-Za-z0-9]+/g, "_") + ".png";
      o.assetNodeId = node.id; // export with node.exportAsync({format:"PNG"}) as a second step
    } else {
      const f = await paintToFill(node.fills);
      if (f) o.fill = f;
    }
  }
  if ("strokes" in node && node.strokes.length) {
    const s = await paintToFill(node.strokes);
    if (s) o.stroke = { ...s, width: node.strokeWeight === figma.mixed ? 1 : node.strokeWeight };
  }
  if ("cornerRadius" in node) {
    o.radius = node.cornerRadius === figma.mixed ? node.topLeftRadius : node.cornerRadius;
  }

  if ("layoutMode" in node) {
    const mode = node.layoutMode === "GRID" ? "NONE" : node.layoutMode;
    o.layout = { mode };
    if (mode !== "NONE") {
      o.layout.spacing = node.itemSpacing;
      o.layout.padding = [node.paddingLeft, node.paddingTop, node.paddingRight, node.paddingBottom];
      o.layout.primaryAlign = node.primaryAxisAlignItems;
      o.layout.counterAlign = node.counterAxisAlignItems === "BASELINE" ? "MIN" : node.counterAxisAlignItems;
    }
  }

  if (t === "TEXT") {
    const f = await paintToFill(node.fills === figma.mixed ? [] : node.fills);
    o.text = {
      characters: node.characters,
      size: node.fontSize === figma.mixed ? 16 : node.fontSize,
      family: node.fontName === figma.mixed ? undefined : node.fontName.family,
      align: node.textAlignHorizontal,
      autoResize: node.textAutoResize === "NONE" ? "NONE"
        : node.textAutoResize === "HEIGHT" ? "HEIGHT" : "WIDTH_AND_HEIGHT",
    };
    if (f) o.text.color = f;
  }

  if (t === "INSTANCE") {
    const main = await node.getMainComponentAsync();
    if (main) {
      const set = main.parent && main.parent.type === "COMPONENT_SET" ? main.parent : null;
      o.component = set ? set.name + "/" + main.name : main.name;
      const mainType = main.getPluginData && main.getPluginData("godotType");
      if (mainType && !o.godotType) o.godotType = mainType;
    }
    const props = {};
    for (const [key, p] of Object.entries(node.componentProperties || {})) {
      props[key.split("#")[0].trim().toLowerCase()] = p.value;
    }
    if (Object.keys(props).length) o.properties = props;
  }

  if ("children" in node) {
    o.children = [];
    for (const ch of node.children) {
      const c = await exportNode(ch, node);
      if (c) o.children.push(c);
    }
  }
  return o;
}

async function exportDesign() {
  let frames = figma.currentPage.selection.filter((n) => n.type === "FRAME");
  if (!frames.length) frames = figma.currentPage.children.filter((n) => n.type === "FRAME");
  const tokens = await exportCollections();
  const out = { schema: SCHEMA, file: figma.root.name, ...tokens, frames: [] };
  for (const f of frames) out.frames.push(await exportNode(f, null));
  return out;
}

// For use_figma / a plugin: the returned value is the design JSON.
return await exportDesign();
