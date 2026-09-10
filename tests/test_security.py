from pathlib import Path
from core.security import SecurityManager


def test_security_manager(tmp_path):
    storage_file = tmp_path / "allowed_users.json"
    sec = SecurityManager(filepath=str(storage_file))

    # Добавление пользователя
    assert sec.add_user(123456789) is True
    assert sec.is_allowed(123456789) is True

    # Повторное добавление
    assert sec.add_user(123456789) is False

    # Проверка сохранения и загрузки из файла
    sec2 = SecurityManager(filepath=str(storage_file))
    assert sec2.is_allowed(123456789) is True
    assert 123456789 in sec2.get_allowed_users()

    # Удаление пользователя
    assert sec2.remove_user(123456789) is True
    assert sec2.is_allowed(123456789) is False
