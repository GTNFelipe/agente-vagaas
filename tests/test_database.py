import pytest
from unittest.mock import patch, MagicMock
from modules.database import vaga_ja_processada, salvar_vaga_base

def test_vaga_ja_processada_true(mocker):
    mock_supabase = mocker.patch("modules.database.supabase")
    mock_response = MagicMock()
    mock_response.data = [{"id": 1}]
    
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    
    assert vaga_ja_processada("url_test") == True

def test_vaga_ja_processada_false(mocker):
    mock_supabase = mocker.patch("modules.database.supabase")
    mock_response = MagicMock()
    mock_response.data = []
    
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    
    assert vaga_ja_processada("url_test") == False

def test_salvar_vaga_base(mocker):
    mock_supabase = mocker.patch("modules.database.supabase")
    mock_response = MagicMock()
    mock_response.data = [{"id": 10}]
    
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
    
    vaga_data = {
        "titulo": "Dev",
        "empresa": "Tech",
        "localizacao": "SP",
        "link": "http",
        "descricao": "Desc"
    }
    
    vaga_id = salvar_vaga_base(vaga_data)
    assert vaga_id == 10
