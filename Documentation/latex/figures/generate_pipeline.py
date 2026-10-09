"""
Script to generate Figure 1: Pipeline Architecture Diagram for ENAHO Poverty Classification.
Outputs high-resolution vector PDF and PNG in Documentation/latex/figures/
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ArrowStyle

def create_pipeline_diagram():
    # Figure setup: horizontal pipeline spanning textwidth
    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis('off')

    # Palette
    c_pucp_dark = '#015D34'    # Primary dark green
    c_pucp_teal = '#009A74'    # Secondary teal
    c_mint = '#E8F5E9'         # Light green background
    c_light_teal = '#E0F2F1'   # Light teal background
    c_border_gray = '#CBD5E1'  # Light gray border
    c_text_dark = '#0F172A'    # Charcoal text
    c_text_muted = '#475569'   # Slate gray text

    # Helper for rounded box
    def draw_box(x, y, w, h, title, subtitle, items, bg_color, border_color, border_w=1.2, title_color=c_pucp_dark):
        box = FancyBboxPatch((x, y), w, h,
                             boxstyle="round,pad=0.5,rounding_size=1.2",
                             facecolor=bg_color, edgecolor=border_color,
                             linewidth=border_w, zorder=2)
        ax.add_patch(box)
        
        # Title
        ax.text(x + w/2, y + h - 2.5, title, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color=title_color, zorder=3)
        
        # Subtitle
        if subtitle:
            ax.text(x + w/2, y + h - 5.0, subtitle, ha='center', va='center',
                    fontsize=6.8, fontstyle='italic', color=c_text_muted, zorder=3)
            curr_y = y + h - 7.5
        else:
            curr_y = y + h - 5.0
            
        # Items
        for item in items:
            ax.text(x + 1.2, curr_y, item, ha='left', va='center',
                    fontsize=6.8, color=c_text_dark, zorder=3)
            curr_y -= 2.6

    # 1. Block 1: Ingesta Multimodular (x: 1.5 to 22.5)
    draw_box(1.5, 3.5, 21.0, 46.5,
             "1. Fuentes ENAHO",
             "Microdatos INEI (2024-2025)",
             [
                 r"$\mathbf{M\acute{o}d.\ 01:}$ Vivienda (Hogar)",
                 "  Materiales, agua, saneam.",
                 r"$\mathbf{M\acute{o}d.\ 02:}$ Demografía (Pers.)",
                 "  Edades, parentesco, sexo",
                 r"$\mathbf{M\acute{o}d.\ 03:}$ Educación (Pers.)",
                 "  Años educ., nivel jefe",
                 r"$\mathbf{M\acute{o}d.\ 05:}$ Empleo (Pers.)",
                 "  Informalidad, pensión",
                 "─────────────────────",
                 r"$\mathbf{M\acute{o}d.\ 34:}$ Sumaria",
                 r"  $\mathbf{POBREZA} \to y_i \in \{0, 1\}$",
                 "  (18.6% pobres / 81.4% no)"
             ],
             bg_color='#F8FAFC', border_color=c_border_gray)

    # 2. Block 2: Operadores de Ingeniería (x: 25.5 to 49.5)
    draw_box(25.5, 3.5, 24.0, 46.5,
             "2. Operadores de Datos",
             "Resolución de Retos del EDA",
             [
                 r"$\mathbf{HousingCohortImputer:}$",
                 "  Propagación intra-predio",
                 r"  $\to$ 2.15% nulos cohabitación",
                 "",
                 r"$\mathbf{HouseholdAggregator\ \Phi(\cdot):}$",
                 r"  • Rama Jefe ($P203 = 1$)",
                 "  • Rama Colectiva (dep., ocup.)",
                 r"  $\to$ Resuelve grano $1:M$",
                 "",
                 r"$\mathbf{DomainBinner:}$",
                 "  Pisos/Paredes en 3 estratos",
                 r"  $\to$ Controla colas $< 0.8\%$",
                 "─────────────────────",
                 r"$\mathbf{Cortafuegos\ Zero\text{-}Leak:}$",
                 "  Aislamiento total de gastos"
             ],
             bg_color=c_mint, border_color=c_pucp_dark)

    # 3. Block 3: Espacio X y Modelos (x: 52.5 to 75.5)
    draw_box(52.5, 3.5, 23.0, 46.5,
             r"3. Espacio $\mathbf{X}$ y Modelos",
             r"Matriz $\mathbf{X} \in \mathbf{R}^{N \times d}$ ($N=5,571$)",
             [
                 r"$\mathbf{Vector\ Concatenado:}$",
                 r"  $\mathbf{x}_i = [\mathbf{x}_i^{\mathrm{viv}}, \mathbf{x}_i^{\mathrm{dem}}, \mathbf{x}_i^{\mathrm{edu}}, \mathbf{x}_i^{\mathrm{emp}}]$",
                 "",
                 r"$\mathbf{Modelos\ Supervisados:}$",
                 "  1. Regresión Logística",
                 "     Penalización ElasticNet",
                 "  2. Árbol CART Podado",
                 r"     Impureza Gini / $\alpha$",
                 "  3. Random Forest",
                 "     Ensamble Bagging",
                 "  4. LightGBM Cost-Sensitive",
                 r"     $\mathbf{scale\_pos\_weight=4.37}$"
             ],
             bg_color=c_light_teal, border_color=c_pucp_teal)

    # 4. Block 4: Inferencia y Validación (x: 78.5 to 98.5)
    draw_box(78.5, 3.5, 20.0, 46.5,
             "4. Inferencia y Test",
             "Mitigación de Error Social",
             [
                 r"$\mathbf{Score\ Probabil\acute{\imath}stico:}$",
                 r"  $\hat{p}_i = P(y_i=1 \mid \mathbf{x}_i) \in [0, 1]$",
                 "",
                 r"$\mathbf{Calibraci\acute{o}n\ Umbral\ \tau^*:}$",
                 r"  $\hat{y}_i = \mathbf{1}(\hat{p}_i \geq \tau^*) \in \{0, 1\}$",
                 r"  $\tau^* \approx 0.30 \to \mathrm{Recall} \geq 70\%$",
                 "",
                 r"$\mathbf{Evaluaci\acute{o}n\ Out\text{-}of\text{-}Time:}$",
                 "  Entrenamiento: ENAHO 2024",
                 "  Prueba Ciega: ENAHO 2025",
                 "",
                 r"$\mathbf{Auditor\acute{\imath}a\ XAI:}$",
                 "  TreeSHAP (no linealidades)"
             ],
             bg_color='#F1F5F9', border_color=c_border_gray)

    # Arrows between blocks
    arrow_style = ArrowStyle("Simple, tail_width=1.0, head_width=3.2, head_length=3.5")
    
    # Arrow 1 -> 2
    arr1 = patches.FancyArrowPatch((22.5, 27.0), (25.5, 27.0), arrowstyle=arrow_style,
                                  facecolor=c_pucp_dark, edgecolor=c_pucp_dark, zorder=5)
    ax.add_patch(arr1)

    # Arrow 2 -> 3
    arr2 = patches.FancyArrowPatch((49.5, 27.0), (52.5, 27.0), arrowstyle=arrow_style,
                                  facecolor=c_pucp_dark, edgecolor=c_pucp_dark, zorder=5)
    ax.add_patch(arr2)

    # Arrow 3 -> 4
    arr3 = patches.FancyArrowPatch((75.5, 27.0), (78.5, 27.0), arrowstyle=arrow_style,
                                  facecolor=c_pucp_teal, edgecolor=c_pucp_teal, zorder=5)
    ax.add_patch(arr3)

    plt.tight_layout()
    plt.savefig('Documentation/latex/figures/pipeline_architecture.pdf', format='pdf', bbox_inches='tight')
    plt.savefig('Documentation/latex/figures/pipeline_architecture.png', format='png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Figure 1 generated successfully: PDF and PNG.")

if __name__ == '__main__':
    create_pipeline_diagram()
