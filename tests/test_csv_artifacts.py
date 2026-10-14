import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('package_outputs',Path(__file__).resolve().parents[1]/'scripts/package_outputs.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_utf8_csv_validation(tmp_path):
    p=tmp_path/'data.csv';p.write_text('Event Name,Estimated Area\n"Spill, α",2 ha\n',encoding='utf-8-sig')
    result=module.audit_csv(p)
    assert result['rows']==1 and result['columns']==2
    assert result['encoding']=='UTF-8 with BOM'
    assert result['duplicate_identity_count']==0


def test_bad_column_count_rejected(tmp_path):
    p=tmp_path/'bad.csv';p.write_text('a,b\n1\n')
    with pytest.raises(ValueError):module.audit_csv(p)


def test_duplicate_rows_and_missing_values(tmp_path):
    p=tmp_path/'data.csv';p.write_text('Event Name,Estimated Area\nSpill,\nSpill,\n')
    result=module.audit_csv(p)
    assert result['identical_duplicate_rows']==1 and result['duplicate_identity_count']==1
    assert result['missing_values']['Estimated Area']==2
