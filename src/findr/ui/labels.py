from findr.domain.models import ResultGroup, ResultKind

TOP_HIT_TITLE = "Melhor resultado"

_KIND_TITLES = {
    ResultKind.CALCULATION: "Calculadora",
    ResultKind.APPLICATION: "Aplicativos",
    ResultKind.FOLDER: "Pastas",
    ResultKind.FILE: "Documentos",
    ResultKind.WEB: "Web",
}


def group_title(group: ResultGroup) -> str:
    return TOP_HIT_TITLE if group.kind is None else _KIND_TITLES[group.kind]
