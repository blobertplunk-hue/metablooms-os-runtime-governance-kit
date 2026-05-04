import json, pathlib, tempfile, importlib.util
p=pathlib.Path('/mnt/data/Metablooms_OS/0_kernel/cartridges/automatic_process_tracker/automatic_process_tracker_emitter_v1.py')
spec=importlib.util.spec_from_file_location('emitter', p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
with tempfile.TemporaryDirectory() as td:
    data=mod.emit(td,'TEST_STAGE','PREV','AUTH.zip',['boot','verify'],1,'active')
    assert data['stage']=='TEST_STAGE'
    assert pathlib.Path(td,'runtime/state/ACTIVE_PROCESS_TRACKER_PREVIEW.txt').exists()
    assert pathlib.Path(td,'runtime/state/ACTIVE_PROCESS_TRACKER_PREVIEW.json').exists()
print('automatic tracker emitter fixture PASS')
