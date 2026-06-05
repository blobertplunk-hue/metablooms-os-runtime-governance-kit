from pathlib import Path
import json
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
def test_fetch_contract_doc_exists():
    assert (ROOT/'GITHUB_FETCH_CONTRACT.md').read_text()
def test_registry_update_prep_contract_doc_exists():
    assert (ROOT/'REGISTRY_UPDATE_PREP_CONTRACT.md').read_text()
def test_registry_indexes_validate():
    reg=json.loads(Path('governance/chat_work_registry/registered_chats.index.json').read_text())
    q=json.loads(Path('governance/chat_work_registry/promotion_queue.index.json').read_text())
    rs=json.loads((ROOT/'schemas/github_registry_index.schema.json').read_text())
    qs=json.loads((ROOT/'schemas/github_promotion_queue.schema.json').read_text())
    Draft202012Validator(rs).validate(reg)
    Draft202012Validator(qs).validate(q)
