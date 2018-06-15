# coding=utf-8
"""
Documentation, License etc.

@package module
"""
import module
from importlib import reload

module.proceedMessage()

if module.updateScript():
    import module
    reload(module)

module.main()
