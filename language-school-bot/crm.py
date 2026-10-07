import os
import logging
import requests

logger = logging.getLogger(__name__)

TWENTY_API_URL = os.getenv("TWENTY_API_URL", "http://localhost:3000")
TWENTY_API_KEY = os.getenv("TWENTY_API_KEY", "")

REST_BASE = f"{TWENTY_API_URL}/rest"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {TWENTY_API_KEY}",
        "Content-Type": "application/json",
    }


def _create_person(name: str, phone: str) -> tuple[str | None, str]:
    if not TWENTY_API_KEY:
        return None, "TWENTY_API_KEY не задан"

    first_name, *rest = name.strip().split(maxsplit=1)
    last_name = rest[0] if rest else ""

    payload = {
        "name": {
            "firstName": first_name,
            "lastName": last_name,
        },
        "phones": {
            "primaryPhoneNumber": phone,
            "primaryPhoneCountryCode": "KZ",
        },
    }

    try:
        r = requests.post(
            f"{REST_BASE}/people",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        res_data = r.json()
        person_id = res_data.get("id") or res_data.get("data", {}).get("id")
        logger.info("TwentyCRM: контакт создан, person_id=%s", person_id)
        return person_id, ""

    except requests.HTTPError as e:
        msg = f"HTTP {e.response.status_code}: {e.response.text[:300]}"
        logger.error("TwentyCRM person error: %s", msg)
        return None, msg
    except requests.RequestException as e:
        logger.error("TwentyCRM person error: %s", e)
        return None, str(e)


def _create_opportunity(name: str, person_id: str | None) -> tuple[str | None, str]:
    payload = {
        "name": name,
        "stage": "NEW",
        "amount": {
            "amountMicros": 0,
            "currencyCode": "KZT",
        },
    }
    if person_id:
        payload["pointOfContactId"] = person_id

    try:
        r = requests.post(
            f"{REST_BASE}/opportunities",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        res_data = r.json()
        opp_id = res_data.get("id") or res_data.get("data", {}).get("id")
        logger.info("TwentyCRM: лид создан, opportunity_id=%s", opp_id)
        return opp_id, ""

    except requests.HTTPError as e:
        msg = f"HTTP {e.response.status_code}: {e.response.text[:300]}"
        logger.error("TwentyCRM opportunity error: %s", msg)
        return None, msg
    except requests.RequestException as e:
        logger.error("TwentyCRM opportunity error: %s", e)
        return None, str(e)


def _create_note(opportunity_id: str, body: str, person_id: str | None = None) -> None:
    """Создаёт заметку и раздельно привязывает её к Opportunity и Person."""
    # 1. Передаём ТОЛЬКО title и body при создании заметки
    note_payload = {
        "title": "Заявка из Telegram",
        "body": body,
    }
    try:
        r = requests.post(
            f"{REST_BASE}/notes",
            json=note_payload,
            headers=_headers(),
            timeout=10,
        )
        if not r.ok:
            logger.error("TwentyCRM note creation failed [%s]: %s", r.status_code, r.text)
            return

        res_data = r.json()
        note_id = (
            res_data.get("id")
            or res_data.get("data", {}).get("id")
            or res_data.get("data", {}).get("createNote", {}).get("id")
        )

        if not note_id:
            logger.error("TwentyCRM: не удалось получить note_id из ответа: %s", res_data)
            return

        logger.info("TwentyCRM: заметка создана, note_id=%s", note_id)

        # 2. Привязываем заметку к Сделке (Opportunity)
        target_payload = {
            "noteId": note_id,
            "opportunityId": opportunity_id,
        }
        r_target = requests.post(
            f"{REST_BASE}/noteTargets",
            json=target_payload,
            headers=_headers(),
            timeout=10,
        )
        if not r_target.ok:
            logger.error("TwentyCRM noteTarget (opportunity) failed [%s]: %s", r_target.status_code, r_target.text)
        else:
            logger.info("TwentyCRM: заметка привязана к Opportunity")

        # 3. Привязываем заметку к Контакту (Person)
        if person_id:
            requests.post(
                f"{REST_BASE}/noteTargets",
                json={
                    "noteId": note_id,
                    "personId": person_id,
                },
                headers=_headers(),
                timeout=10,
            )

    except requests.RequestException as e:
        logger.error("TwentyCRM note error: %s", e)


def create_lead(data: dict) -> tuple[bool, str]:
    if not TWENTY_API_KEY:
        logger.warning("TwentyCRM: TWENTY_API_KEY не задан — пропускаем.")
        return False, "TWENTY_API_KEY не задан"

    # 1. Создаём контакт
    person_id, person_err = _create_person(data["name"], data["phone"])

    # 2. Создаём лид (название с деталями)
    opp_name = f"[Telegram] {data['name']} — {data['language']} ({data['level']}, {data['format']})"
    opp_id, opp_err = _create_opportunity(opp_name, person_id)

    if not opp_id:
        return False, opp_err or person_err

    # 3. Добавляем заметку
    note_body = (
        f"📱 Телефон: {data['phone']}\n"
        f"🌍 Язык: {data['language']}\n"
        f"📊 Уровень: {data['level']}\n"
        f"📋 Формат: {data['format']}\n"
        f"💬 Telegram ID: {data['telegram_id']}\n"
        f"🔗 Telegram: @{data['telegram_username']}\n"
        f"📍 Источник: {data['source']}"
    )
    _create_note(opp_id, note_body, person_id)

    return True, f"opportunity_id={opp_id}"