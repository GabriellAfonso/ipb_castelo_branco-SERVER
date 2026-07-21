"""Seed fake members with birthdays spread across all 12 months for local testing."""

from datetime import date

from django.core.management.base import BaseCommand

from features.members.models.member import Member


FAKE_MEMBERS = [
    ("Ana Silva", "F", date(1995, 1, 8)),
    ("Bruno Costa", "M", date(1988, 1, 22)),
    ("Carla Souza", "F", date(1990, 2, 14)),
    ("Daniel Oliveira", "M", date(1985, 2, 28)),
    ("Elena Pereira", "F", date(1992, 3, 5)),
    ("Felipe Santos", "M", date(1987, 3, 19)),
    ("Gabriela Lima", "F", date(1993, 4, 2)),
    ("Hugo Almeida", "M", date(1991, 4, 17)),
    ("Isabela Rocha", "F", date(1989, 5, 10)),
    ("Joao Ferreira", "M", date(1994, 5, 25)),
    ("Karen Barbosa", "F", date(1986, 6, 7)),
    ("Lucas Ribeiro", "M", date(1996, 6, 21)),
    ("Marina Cardoso", "F", date(1990, 7, 3)),
    ("Nicolas Araujo", "M", date(1988, 7, 16)),
    ("Olivia Gomes", "F", date(1993, 7, 30)),
    ("Pedro Martins", "M", date(1985, 8, 11)),
    ("Raquel Dias", "F", date(1992, 8, 24)),
    ("Samuel Nunes", "M", date(1987, 9, 1)),
    ("Tatiana Campos", "F", date(1991, 9, 18)),
    ("Vinicius Moreira", "M", date(1994, 10, 6)),
    ("Wanda Teixeira", "F", date(1989, 10, 20)),
    ("Xavier Mendes", "M", date(1996, 11, 9)),
    ("Yasmin Castro", "F", date(1986, 11, 27)),
    ("Zeca Pinto", "M", date(1990, 12, 4)),
    ("Amanda Correia", "F", date(1988, 12, 25)),
    ("Roberto Lopes", None, date(1993, 3, 12)),
    ("Fernanda Nascimento", "F", date(1991, 7, 7)),
    ("Gustavo Ramos", "M", date(1985, 1, 31)),
    ("Juliana Vieira", "F", date(1992, 6, 15)),
    ("Marcos Azevedo", "M", date(1987, 12, 18)),
]


class Command(BaseCommand):
    help = "Seed fake members with birthdays for local testing"

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove seeded members before creating new ones",
        )

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        if options["clear"]:
            deleted, _ = Member.objects.filter(
                name__in=[name for name, _, _ in FAKE_MEMBERS]
            ).delete()
            self.stdout.write(f"Removed {deleted} seeded members.")
            return

        created = 0
        for name, gender, birth_date in FAKE_MEMBERS:
            _, was_created = Member.objects.get_or_create(
                name=name,
                defaults={
                    "gender": gender,
                    "birth_date": birth_date,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            f"Created {created} members ({len(FAKE_MEMBERS) - created} already existed)."
        )
