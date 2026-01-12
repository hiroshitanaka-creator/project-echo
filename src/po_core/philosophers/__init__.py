"""
Po_core Philosophers Module

This module contains the philosophical reasoning engines.
Each philosopher represents a different perspective and approach to meaning generation.

Loader Functions:
- load_all_philosophers(): Load all 39 philosophers
- load_cosmic_philosophers(): Load philosophers for Cosmic Ethics 39 scenarios
"""

from po_core.philosophers.arendt import Arendt
from po_core.philosophers.aristotle import Aristotle
from po_core.philosophers.badiou import Badiou
from po_core.philosophers.base import Philosopher, PhilosopherPerspective
from po_core.philosophers.beauvoir import Beauvoir
from po_core.philosophers.butler import Butler
from po_core.philosophers.confucius import Confucius
from po_core.philosophers.deleuze import Deleuze
from po_core.philosophers.derrida import Derrida
from po_core.philosophers.descartes import Descartes
from po_core.philosophers.dewey import Dewey
from po_core.philosophers.dogen import Dogen
from po_core.philosophers.epicurus import Epicurus
from po_core.philosophers.foucault import Foucault
from po_core.philosophers.hegel import Hegel
from po_core.philosophers.heidegger import Heidegger
from po_core.philosophers.husserl import Husserl
from po_core.philosophers.jonas import Jonas
from po_core.philosophers.jung import Jung
from po_core.philosophers.kant import Kant
from po_core.philosophers.kierkegaard import Kierkegaard
from po_core.philosophers.lacan import Lacan
from po_core.philosophers.laozi import Laozi
from po_core.philosophers.levinas import Levinas
from po_core.philosophers.marcus_aurelius import MarcusAurelius
from po_core.philosophers.merleau_ponty import MerleauPonty
from po_core.philosophers.nagarjuna import Nagarjuna
from po_core.philosophers.nietzsche import Nietzsche
from po_core.philosophers.nishida import Nishida
from po_core.philosophers.parmenides import Parmenides
from po_core.philosophers.peirce import Peirce
from po_core.philosophers.plato import Plato
from po_core.philosophers.sartre import Sartre
from po_core.philosophers.schopenhauer import Schopenhauer
from po_core.philosophers.spinoza import Spinoza
from po_core.philosophers.wabi_sabi import WabiSabi
from po_core.philosophers.watsuji import Watsuji
from po_core.philosophers.weil import Weil
from po_core.philosophers.wittgenstein import Wittgenstein
from po_core.philosophers.zhuangzi import Zhuangzi

__all__ = [
    "Philosopher",
    "PhilosopherPerspective",
    "Arendt",
    "Aristotle",
    "Badiou",
    "Beauvoir",
    "Butler",
    "Confucius",
    "Deleuze",
    "Derrida",
    "Descartes",
    "Dewey",
    "Dogen",
    "Epicurus",
    "Foucault",
    "Hegel",
    "Heidegger",
    "Husserl",
    "Jonas",
    "Jung",
    "Kant",
    "Kierkegaard",
    "Lacan",
    "Laozi",
    "Levinas",
    "MarcusAurelius",
    "MerleauPonty",
    "Nagarjuna",
    "Nietzsche",
    "Nishida",
    "Parmenides",
    "Peirce",
    "Plato",
    "Sartre",
    "Schopenhauer",
    "Spinoza",
    "WabiSabi",
    "Watsuji",
    "Weil",
    "Wittgenstein",
    "Zhuangzi",
    "load_all_philosophers",
    "load_cosmic_philosophers",
]


def load_all_philosophers() -> list[Philosopher]:
    """
    Load all 39 philosophers.

    Returns:
        List of all philosopher instances
    """
    return [
        Arendt(),
        Aristotle(),
        Badiou(),
        Beauvoir(),
        Butler(),
        Confucius(),
        Deleuze(),
        Derrida(),
        Descartes(),
        Dewey(),
        Dogen(),
        Epicurus(),
        Foucault(),
        Hegel(),
        Heidegger(),
        Husserl(),
        Jonas(),
        Jung(),
        Kant(),
        Kierkegaard(),
        Lacan(),
        Laozi(),
        Levinas(),
        MarcusAurelius(),
        MerleauPonty(),
        Nagarjuna(),
        Nietzsche(),
        Nishida(),
        Parmenides(),
        Peirce(),
        Plato(),
        Sartre(),
        Schopenhauer(),
        Spinoza(),
        WabiSabi(),
        Watsuji(),
        Weil(),
        Wittgenstein(),
        Zhuangzi(),
    ]


# Cosmic Ethics 39 set - philosophers particularly relevant to long-term thinking
COSMIC_SET = {
    "Immanuel Kant",  # Universal law and categorical imperative
    "和辻哲郎 (Watsuji Tetsurō)",  # Relational ethics and betweenness
    "Jean-Paul Sartre",  # Existence and responsibility
    "Hans Jonas",  # Responsibility for future generations
    "नागार्जुन (Nāgārjuna)",  # Emptiness and interdependence
    "Hannah Arendt",  # Political responsibility and plurality
    "Baruch Spinoza",  # Ethics and necessity
    "Emmanuel Levinas",  # Responsibility for the Other
    "Simone Weil",  # Justice and attention
    "Confucius (孔子)",  # Relational ethics and ritual
    "Laozi (老子)",  # Non-interference and natural flow
    "Dōgen (道元)",  # Temporal existence and practice
    "Nishida Kitarō (西田幾多郎)",  # Place and absolute nothingness
    "Aristotle",  # Practical wisdom and virtue
    "Plato",  # Forms and the Good
    "Martin Heidegger",  # Being and time
    "Simone de Beauvoir",  # Ethics of ambiguity
    "Judith Butler",  # Precarity and relationality
    "Gilles Deleuze",  # Difference and multiplicity
}


def load_cosmic_philosophers() -> list[Philosopher]:
    """
    Load philosophers particularly relevant to Cosmic Ethics 39 scenarios.

    This subset focuses on philosophers with strong views on:
    - Long-term responsibility
    - Universal principles
    - Relational ethics
    - Existential and cosmological questions

    Returns:
        List of cosmic ethics philosophers
    """
    all_philosophers = load_all_philosophers()
    return [p for p in all_philosophers if p.name in COSMIC_SET]
