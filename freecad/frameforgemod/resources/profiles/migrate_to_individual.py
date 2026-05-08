import os, FreeCAD as App

LIB_FILE = os.path.join(App.getUserAppDataDir(), "Mod", "frameforgemod", "freecad", "frameforgemod", "resources", "profiles", "AluminumProfiles.FCStd")
OUT_DIR  = os.path.join(App.getUserAppDataDir(), "Mod", "frameforgemod", "freecad", "frameforgemod", "resources", "profiles", "aluminum")

os.makedirs(OUT_DIR, exist_ok=True)
lib_doc = App.openDocument(LIB_FILE, True)
sketches = [o for o in lib_doc.Objects if o.TypeId == "Sketcher::SketchObject" and hasattr(o, "Shape") and o.Shape]
print(f"Found {len(sketches)} sketches")
for sk in sketches:
    name = (sk.Label or sk.Name).replace(" ", "_").replace("/", "_")
    out = os.path.join(OUT_DIR, f"{name}.FCStd")
    nd = App.newDocument(name)
    nd.copyObject(sk, True)
    nd.recompute()
    nd.saveAs(out)
    App.closeDocument(nd.Name)
    print(f"  {name}")
App.closeDocument(lib_doc.Name)
print("Done! Restart FreeCAD.")
