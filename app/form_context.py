from __future__ import annotations

from app.services.class_service import list_gimnasios, list_profesores, list_tipos_clase


def class_form_context(**kwargs):
    gimnasios = list_gimnasios()
    gimnasio_id = kwargs.get("gimnasio_id") or (str(gimnasios[0].id) if gimnasios else "")
    return {
        "gimnasios": gimnasios,
        "profesores": list_profesores(),
        "tipos_clase": list_tipos_clase(),
        **kwargs,
        "gimnasio_id": gimnasio_id,
    }
