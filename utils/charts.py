import matplotlib.pyplot as plt
import io
import discord

def generuj_wykres_elo(nick, elo_history):
    """
    Generuje wykres ELO i zwraca go jako obiekt discord.File.
    """
    if not elo_history or len(elo_history) < 2:
        return None

    # Ustawienia stylu (Dark Mode)
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Kolory
    line_color = '#ff5500' # Faceit Orange
    grid_color = '#333333'
    
    # Rysowanie linii
    ax.plot(elo_history, marker='o', linestyle='-', color=line_color, linewidth=3, markersize=8, label='ELO')
    
    # Wypełnienie pod linią
    ax.fill_between(range(len(elo_history)), elo_history, min(elo_history) - 50, color=line_color, alpha=0.1)

    # Konfiguracja osi
    ax.set_title(f"Historia ELO - {nick}", fontsize=16, fontweight='bold', pad=20, color='white')
    ax.set_xlabel("Ostatnie Mecze", fontsize=12, labelpad=10)
    ax.set_ylabel("Punkty ELO", fontsize=12, labelpad=10)
    
    # Siatka
    ax.grid(True, linestyle='--', alpha=0.3, color=grid_color)
    
    # Usuwanie ramek (spines)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Dynamiczne limity osi Y dla lepszego wyglądu
    margin = 50
    ax.set_ylim(min(elo_history) - margin, max(elo_history) + margin)

    # Dodawanie wartości nad punktami
    for i, val in enumerate(elo_history):
        ax.annotate(f'{val}', (i, val), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color='white', alpha=0.8)

    # Zapis do bufora
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=120)
    buf.seek(0)
    plt.close(fig)
    
    return discord.File(buf, filename="wykres_elo.png")
