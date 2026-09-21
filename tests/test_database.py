import pytest
from unittest.mock import MagicMock
from modules.database import vaga_ja_processada, salvar_vaga_base

def test_vaga_ja_processada_true(mocker):
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [{"id": 1}]
    
    mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    
    assert vaga_ja_processada(mock_supabase, "http://url_test") == True

def test_vaga_ja_processada_false(mocker):
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    mock_response.data = []
    
    mock_supabase.table.return_value.select.return_value.ilike.return_value.execute.return_value = mock_response
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    
    assert vaga_ja_processada(mock_supabase, "http://url_test") == False

def test_salvar_vaga_base(mocker):
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [{"id": 10}]
    
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response
    
    vaga_data = {
        "titulo": "Dev",
        "empresa": "Tech",
        "localizacao": "SP",
        "link": "http://url_test",
        "descricao": "Desc"
    }
    
    vaga_id = salvar_vaga_base(mock_supabase, vaga_data, match_score=90)
    assert vaga_id == 10
