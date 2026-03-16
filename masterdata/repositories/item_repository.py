from typing import Iterable, Tuple

from django.db import transaction
from django.utils import timezone

from masterdata.models import ArchiveItem, item


def get_item_by_id(item_id: int) -> item:
    """
    Récupère un item par son identifiant primaire.
    Lève item.DoesNotExist si l'item n'existe pas.
    """
    return item.objects.get(pk=item_id)


@transaction.atomic
def archive_item_instance(it: item, commentaire: str | None = None) -> ArchiveItem:
    """
    Archive un item et crée un enregistrement ArchiveItem associé.
    Si l'item est déjà archivé, retourne simplement le dernier ArchiveItem existant.
    """
    if it.archive:
        # Retourner le dernier historique si déjà archivé
        return it.archive_items.last()

    it.archive = True
    it.date_archive = timezone.now().date()
    it.save(update_fields=["archive", "date_archive", "updated_at"])

    return ArchiveItem.objects.create(item_archive=it, commentaire=commentaire or "")


@transaction.atomic
def unarchive_item_instance(it: item) -> None:
    """
    Désarchive un item sans supprimer l'historique ArchiveItem.
    """
    if not it.archive:
        return

    it.archive = False
    it.date_archive = None
    it.save(update_fields=["archive", "date_archive", "updated_at"])


def list_archive_items_by_compte(compte) -> Iterable[ArchiveItem]:
    """
    Retourne tous les ArchiveItem liés au compte donné.
    """
    return (
        ArchiveItem.objects.filter(item_archive__article__compte=compte)
        .select_related(
            "item_archive",
            "item_archive__article",
            "item_archive__article__produit",
            "item_archive__article__produit__categorie",
            "item_archive__emplacement",
            "item_archive__departement",
            "item_archive__affectation_personne",
        )
        .order_by("-created_at")
    )


def bulk_archive_items_from_rows(
    rows: Iterable[Tuple[int, str | None]],
) -> Tuple[int, int, int]:
    """
    Archive en masse des items à partir d'une liste de tuples (item_id, commentaire).

    Retourne un tuple (total, success, already_archived).
    Les erreurs (item introuvable, etc.) ne sont pas comptées comme succès.
    """
    total = 0
    success = 0
    already_archived = 0

    with transaction.atomic():
        for item_id, commentaire in rows:
            total += 1
            try:
                it = get_item_by_id(item_id)
            except item.DoesNotExist:
                continue

            if it.archive:
                already_archived += 1
                continue

            archive_item_instance(it, commentaire)
            success += 1

    return total, success, already_archived

