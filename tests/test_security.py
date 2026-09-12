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


def test_security_manager_detailed_profile(tmp_path):
    storage_file = tmp_path / "allowed_users.json"
    sec = SecurityManager(filepath=str(storage_file))

    # Добавление с именем и юзернеймом
    assert sec.add_user(999, first_name="Иван", last_name="Иванов", username="ivan999") is True

    detailed = sec.get_users_detailed()
    user_999 = next((u for u in detailed if u["user_id"] == 999), None)
    assert user_999 is not None
    assert user_999["first_name"] == "Иван"
    assert user_999["last_name"] == "Иванов"
    assert user_999["username"] == "ivan999"

    # Обновление информации на лету (middleware)
    sec.update_user_info(999, first_name="Иван", last_name="Петров", username="ivan_new")
    detailed_updated = sec.get_users_detailed()
    user_999_upd = next((u for u in detailed_updated if u["user_id"] == 999), None)
    assert user_999_upd["last_name"] == "Петров"
    assert user_999_upd["username"] == "ivan_new"

