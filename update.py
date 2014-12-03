'''
Documentation, License etc.

@package module
'''
import module

if module.updateScript():
    import module
    reload(module)

module.main()
