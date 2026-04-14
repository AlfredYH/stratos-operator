import os
import importlib

FACTOR_REGISTRY = {}

folder = os.path.dirname(__file__)

for fname in os.listdir(folder):
    if fname.endswith(".py") and fname != "__init__.py":
        mod_name = fname[:-3]
        mod = importlib.import_module(f".{mod_name}", package="quant.factors")
        if hasattr(mod, "calculate"):
            FACTOR_REGISTRY[mod_name] = mod.calculate