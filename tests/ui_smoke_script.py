"""Roda as telas (aba do astronauta, da Terra, barra lateral e setas) com um Streamlit de mentira,
para pegar erros de código sem abrir o app. Usado por tests/test_ui_smoke.py."""
import sys, types, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class State(dict):
    __getattr__ = dict.get
    def __setattr__(self, k, v): self[k] = v

class Fake:
    def __init__(self, st): self._st = st
    def __call__(self, *a, **k): return Fake(self._st)
    def __getattr__(self, name): return getattr(self._st, name)
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter([Fake(self._st)] * 4)

class St(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit"); self.session_state = State(); self.sidebar = Fake(self); self.calls = []
    def __getattr__(self, name):
        if name.startswith("__"): raise AttributeError(name)
        def f(*a, **k):
            self.calls.append(name)
            if name in ("columns",):
                n = a[0] if a and isinstance(a[0], int) else len(a[0])
                return [Fake(self) for _ in range(n)]
            if name in ("radio", "selectbox"):
                opts = list(a[1]) if len(a) > 1 else []
                key = k.get("key")
                return self.session_state.get(key) if self.session_state.get(key) in opts else (opts[0] if opts else None)
            if name == "number_input":
                return k.get("value", a[1] if len(a) > 1 else 1) if "value" in k else self.session_state.get(k.get("key"), a[1] if len(a) > 1 else 1)
            if name in ("button", "toggle", "checkbox"): return False
            if name == "tabs": return [Fake(self) for _ in a[0]]
            if name in ("expander", "container", "form"): return Fake(self)
            if name == "text_area": return ""
            return Fake(self)
        return f
    def cache_resource(self, fn=None, **k):
        return fn if fn else (lambda g: g)
    def fragment(self, *a, **k): return lambda g: g

st = St(); sys.modules["streamlit"] = st
class Any:
    def __call__(self, *a, **k): return Any()
    def __getattr__(self, n): return Any()
    def __add__(self, o): return Any()
    def properties(self, **k): return Any()
for m in ("altair",):
    sys.modules[m] = Any.__new__(Any) if False else types.ModuleType(m)
    sys.modules[m].__getattr__ = lambda n: Any()
try:
    import pandas
except ImportError:
    class DF(list):
        def __init__(self, data=None, *a, **k): super().__init__(data if isinstance(data, list) else [])
        def rename(self, **k): return self
        def __getitem__(self, i): return super().__getitem__(i) if isinstance(i, int) else Any()
    pd = types.ModuleType("pandas"); pd.DataFrame = DF; pd.Series = DF; sys.modules["pandas"] = pd
import storage, demo_seed
from support import i18n
storage.init_db()
for day, lang in ((1, "en"), (7, "pt"), (20, "en"), (66, "pt"), (114, "en"), (180, "pt"), (66, "en")):
    i18n.set_lang(lang)
    demo_seed.go_to_day(day)
    st.session_state.pop("earth_view", None)
    from ui import earth_tab, sidebar, day_nav, astronaut_tab
    for view in ("all", "15", "range", "day", "7"):
        st.session_state["earth_view"] = view if view in __import__("ui.earth_data", fromlist=["x"]).view_options(day) else "all"
        for crew in ("T1", "T2", "T4"):
            st.session_state["earth_crew"] = crew; st.session_state["crew"] = crew
            earth_tab.render(); sidebar.render(); day_nav.render(); astronaut_tab.render()
print("smoke ok", len(st.calls))
