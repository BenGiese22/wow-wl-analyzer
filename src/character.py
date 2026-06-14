from src.client import query
from src.constants import CLASS_ID_TO_NAME, CLASS_SPECS
from src.queries import GET_CHARACTER


def lookup_character(token: str, name: str, realm: str, region: str) -> dict:
    data = query(token, GET_CHARACTER, {
        "name": name,
        "serverSlug": realm.lower(),
        "serverRegion": region.upper(),
    })
    char = data["characterData"]["character"]
    if char is None:
        raise ValueError(
            f"Character '{name}-{realm}' ({region}) not found on WCL. "
            "Check spelling — accented characters must match exactly."
        )
    class_name = CLASS_ID_TO_NAME.get(char["classID"], f"Unknown({char['classID']})")
    return {
        "name": char["name"],
        "class_id": char["classID"],
        "class_name": class_name,
    }


def get_specs_for_class(class_name: str) -> list[str]:
    return list(CLASS_SPECS.get(class_name, []))
