import io
import discord
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

FACEIT_LEVELS = [
    (1, 0, 500),
    (2, 501, 750),
    (3, 751, 900),
    (4, 901, 1050),
    (5, 1051, 1200),
    (6, 1201, 1350),
    (7, 1351, 1530),
    (8, 1531, 1750),
    (9, 1751, 2000),
    (10, 2001, 99999)
]

FACEIT_THRESHOLDS = [
    (1, 0, 'LVL 1'),
    (2, 501, 'LVL 2 (501 ELO)'),
    (3, 751, 'LVL 3 (751 ELO)'),
    (4, 901, 'LVL 4 (901 ELO)'),
    (5, 1051, 'LVL 5 (1051 ELO)'),
    (6, 1201, 'LVL 6 (1201 ELO)'),
    (7, 1351, 'LVL 7 (1351 ELO)'),
    (8, 1531, 'LVL 8 (1531 ELO)'),
    (9, 1751, 'LVL 9 (1751 ELO)'),
    (10, 2001, 'LVL 10 (2001 ELO)')
]

def _wyznacz_progi_i_zakres(elo_history):
    """
    Wyznacza zakres osi Y oraz listę wszystkich progów Faceit widocznych na ekranie:
    - Zawsze obejmuje linię spadku obecnego poziomu gracza.
    - Jeśli do kolejnego poziomu (awans) brakuje <= 70 ELO, obejmuje go u góry.
    - Wszystkie progi poziomów (np. kilka wbitych poziomów w trakcie 100 meczów), które mieszczą
      się na widocznym ekranie w zakresie [y_min, y_max], zostają wyświetlone.
    """
    min_elo = min(elo_history)
    max_elo = max(elo_history)
    last_elo = elo_history[-1]

    curr_lvl = 1
    for lvl, min_e, max_e in FACEIT_LEVELS:
        if min_e <= last_elo <= max_e:
            curr_lvl = lvl
            break

    y_min = min_elo - 30
    y_max = max_elo + 35

    # 1. Linia spadku obecnego poziomu gracza (obrona rangi)
    if curr_lvl > 1:
        th_spadek = [th for lvl, th, _ in FACEIT_THRESHOLDS if lvl == curr_lvl][0]
        if min_elo - th_spadek <= 250:
            y_min = min(y_min, th_spadek - 25)

    # 2. Cel awansu, jeśli gracz jest do 70 ELO przed kolejnym poziomem
    if curr_lvl < 10:
        th_awans = [th for lvl, th, _ in FACEIT_THRESHOLDS if lvl == curr_lvl + 1][0]
        if th_awans - max_elo <= 70:
            y_max = max(y_max, th_awans + 25)

    # 3. Wyświetl każdy próg, który mieści się na ekranie
    to_draw = []
    for lvl, th, label in FACEIT_THRESHOLDS:
        if th == 0:
            continue
        if y_min <= th <= y_max:
            to_draw.append((th, label))

    to_draw.sort(key=lambda x: x[0])
    return to_draw, y_min, y_max

def generuj_wykres_elo(nick, elo_history):
    """
    Generuje wykres ELO w nowoczesnym ciemnym stylu i zwraca go jako obiekt discord.File.
    """
    if not elo_history or len(elo_history) < 2:
        return None

    elo = list(elo_history)
    n_points = len(elo)
    mecze = np.arange(1, n_points + 1)

    # Ustawienia stylu (Dark Mode)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')

    try:
        # Dynamiczne progi poziomów Faceit i zakres osi Y
        progi, y_min, y_max = _wyznacz_progi_i_zakres(elo)

        # Główna linia
        if n_points <= 10:
            ax.plot(
                mecze, elo, color='#FF5500', linewidth=2.2, zorder=3,
                marker='o', markersize=4, markerfacecolor='#FF5500', markeredgecolor='#121212'
            )
        else:
            ax.plot(mecze, elo, color='#FF5500', linewidth=2.2, zorder=3)

        # Wypełnienie pod linią
        ax.fill_between(mecze, elo, y_min, color='#FF5500', alpha=0.12)

        # Wszystkie linie poziomów widoczne na ekranie
        for th, label in progi:
            is_lvl10 = (th == 2001)
            col = '#FFD700' if is_lvl10 else '#F0B90B'
            alpha = 0.75 if is_lvl10 else 0.55
            linestyle = '--' if is_lvl10 else ':'

            ax.axhline(th, color=col, linestyle=linestyle, linewidth=1.1 if is_lvl10 else 0.9, alpha=alpha, zorder=2)
            ax.annotate(
                label,
                (1, th),
                xytext=(6, 4),
                textcoords='offset points',
                ha='left',
                va='bottom',
                color=col,
                fontsize=8.5 if is_lvl10 else 8,
                alpha=0.9 if is_lvl10 else 0.75,
                fontweight='bold'
            )

        # Wyznaczanie punktów kluczowych: MAX, MIN, AKTUALNY (z zaawansowanym unikaniem kolizji)
        max_idx = int(np.argmax(elo))
        min_idx = int(np.argmin(elo))
        last_idx = n_points - 1

        kluczowe = []
        if max_idx == min_idx:
            # Wszystkie wartości są identyczne
            kluczowe.append((last_idx + 1, elo[last_idx], f"{elo[last_idx]}", '#FFFFFF', (-5, 12), 'right'))
        elif last_idx == max_idx:
            min_ha = 'left' if min_idx == 0 else ('right' if min_idx >= n_points - 3 else 'center')
            kluczowe.append((min_idx + 1, elo[min_idx], f"MIN: {elo[min_idx]}", '#FF5252', (0, -15), min_ha))
            kluczowe.append((last_idx + 1, elo[last_idx], f"MAX / AKTUALNY: {elo[last_idx]}", '#00E676', (-5, 12), 'right'))
        elif last_idx == min_idx:
            max_ha = 'left' if max_idx == 0 else ('right' if max_idx >= n_points - 3 else 'center')
            kluczowe.append((max_idx + 1, elo[max_idx], f"MAX: {elo[max_idx]}", '#00E676', (0, 10), max_ha))
            kluczowe.append((last_idx + 1, elo[last_idx], f"MIN / AKTUALNY: {elo[last_idx]}", '#FF5252', (-5, -15), 'right'))
        else:
            # Trzy różne punkty
            max_ha = 'left' if max_idx == 0 else ('right' if max_idx >= n_points - 3 else 'center')
            min_ha = 'left' if min_idx == 0 else ('right' if min_idx >= n_points - 3 else 'center')

            # Unikanie nakładania się etykiet MAX / MIN z AKTUALNYM:
            blisko_max = (abs(last_idx - max_idx) <= 8 and abs(elo[last_idx] - elo[max_idx]) <= 45)
            blisko_min = (abs(last_idx - min_idx) <= 8 and abs(elo[last_idx] - elo[min_idx]) <= 45)

            if blisko_max and not blisko_min:
                # MAX jest na górze (+10), więc AKTUALNY dajemy na dół (-15)
                last_offset = (-5, -15)
            elif blisko_min and not blisko_max:
                # MIN jest na dole (-15), więc AKTUALNY dajemy na górę (+12)
                last_offset = (-5, 12)
            else:
                if abs(elo[last_idx] - elo[max_idx]) < abs(elo[last_idx] - elo[min_idx]):
                    last_offset = (-5, -15)
                else:
                    last_offset = (-5, 12)

            kluczowe.append((max_idx + 1, elo[max_idx], f"MAX: {elo[max_idx]}", '#00E676', (0, 10), max_ha))
            kluczowe.append((min_idx + 1, elo[min_idx], f"MIN: {elo[min_idx]}", '#FF5252', (0, -15), min_ha))
            kluczowe.append((last_idx + 1, elo[last_idx], f"{elo[last_idx]}", '#FFFFFF', last_offset, 'right'))

        for x_pos, val, label, col, offset, ha in kluczowe:
            ax.scatter(x_pos, val, color=col, s=50, zorder=4, edgecolors='#121212', linewidth=1.5, clip_on=False)
            ax.annotate(
                label, (x_pos, val), xytext=offset, textcoords='offset points',
                ha=ha, va='center', color=col, fontsize=9, fontweight='bold'
            )

        # Siatka i osie - oś X kończy się dokładnie na n_points
        ax.set_xlim(1, n_points)
        if n_points <= 5:
            ax.set_xticks(list(range(1, n_points + 1)))
        else:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        ax.grid(True, linestyle=':', alpha=0.2, color='white')
        ax.set_ylim(y_min, y_max)

        # Usunięcie zbędnych ramek
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color('#333333')

        ax.set_title(f"Historia ELO - {nick}", fontsize=15, fontweight='bold', pad=15, color='white')
        ax.set_xlabel("Ostatnie mecze", fontsize=11, color='#AAAAAA', labelpad=10)
        ax.set_ylabel("Punkty ELO", fontsize=11, color='#AAAAAA', labelpad=10)

        plt.tight_layout()

        # Zapis do bufora
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        return discord.File(buf, filename="wykres_elo.png")
    finally:
        plt.close(fig)
