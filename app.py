import streamlit as st
import pandas as pd
import plotly.express as px
from rdkit import Chem
from rdkit.Chem import Descriptors

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Green Chemistry Metrics Calculator",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Green Chemistry Metrics Calculator")
st.markdown("""
Calculate fundamental green metrics like **Atom Economy ($AE$)**, **Reaction Mass Efficiency ($RME$)**, 
**Process Mass Intensity ($PMI$)**, **E-Factor**, and **Carbon Efficiency ($CE$)** using SMILES and reaction mass logs.
""")

st.divider()

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def analyze_smiles(smiles_str):
    """Parses SMILES and returns molecular weight and carbon count."""
    mol = Chem.MolFromSmiles(smiles_str.strip())
    if mol is None:
        return None, None
    mw = Descriptors.MolWt(mol)
    c_count = sum(1 for atom in mol.GetAtoms() if atom.GetSymbol() == 'C')
    return mw, c_count

# -----------------------------------------------------------------------------
# App Logic / Inputs
# -----------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("1. Reaction Components (SMILES & Masses)")
    
    # Target Product
    st.markdown("### Target Product")
    prod_smiles = st.text_input("Product SMILES", "CC(=O)Oc1ccccc1C(=O)O", key="prod_smiles") # Aspirin
    prod_mass = st.number_input("Mass of Isolated Target Product (g)", min_value=0.0001, value=18.0, step=0.1)
    
    prod_mw, prod_c = analyze_smiles(prod_smiles)
    if prod_mw is None:
        st.error("Invalid Target Product SMILES string!")
    else:
        st.caption(f"**Detected MW:** {prod_mw:.2f} g/mol | **Carbon Count:** {prod_c}")

    st.markdown("---")
    st.markdown("### Reactants")
    
    # Session state for reactants
    if 'reactants' not in st.session_state:
        st.session_state.reactants = [
            {"smiles": "CC(=O)O", "mass": 10.2, "coeff": 1}, # Acetic acid
            {"smiles": "O=C(O)c1ccccc1O", "mass": 13.8, "coeff": 1} # Salicylic acid
        ]

    def add_reactant():
        st.session_state.reactants.append({"smiles": "", "mass": 0.0, "coeff": 1})

    def remove_reactant(idx):
        if len(st.session_state.reactants) > 1:
            st.session_state.reactants.pop(idx)

    reactant_data = []
    for i, r in enumerate(st.session_state.reactants):
        r_cols = st.columns([3, 2, 1, 1])
        s_input = r_cols[0].text_input(f"Reactant {i+1} SMILES", value=r["smiles"], key=f"r_smiles_{i}")
        m_input = r_cols[1].number_input(f"Mass (g)", value=float(r["mass"]), min_value=0.0, step=0.1, key=f"r_mass_{i}")
        c_input = r_cols[2].number_input(f"Coeff", value=int(r["coeff"]), min_value=1, step=1, key=f"r_coeff_{i}")
        
        if r_cols[3].button("🗑️", key=f"del_{i}"):
            remove_reactant(i)
            st.rerun()
            
        mw, c_cnt = analyze_smiles(s_input) if s_input else (0, 0)
        reactant_data.append({
            "smiles": s_input,
            "mass": m_input,
            "coeff": c_input,
            "mw": mw,
            "c_count": c_cnt,
            "valid": mw is not None
        })

    st.button("➕ Add Reactant", on_click=add_reactant)

with col_right:
    st.subheader("2. Process Waste & Solvents")
    
    st.markdown("### Solvents, Reagents & Workup")
    solvents_mass = st.number_input("Reaction Solvents Total Mass (g)", min_value=0.0, value=80.0, step=1.0)
    reagents_mass = st.number_input("Reagents / Catalysts Total Mass (g)", min_value=0.0, value=2.0, step=0.5)
    workup_mass = st.number_input("Workup & Extraction Materials Total Mass (g)", min_value=0.0, value=50.0, step=1.0)
    purification_mass = st.number_input("Purification Media / Silica Gel (g)", min_value=0.0, value=10.0, step=1.0)

    st.markdown("---")
    st.subheader("3. Environmental Penalty Parameters")
    hazard_penalty = st.slider("Solvent/Hazard Risk Multiplier (1 = Very Safe, 5 = High Toxicity)", 1, 5, 2)

# -----------------------------------------------------------------------------
# Calculations & Output
# -----------------------------------------------------------------------------
st.divider()
st.header("📊 Results & Dashboard")

# Validate inputs
all_reactants_valid = all([r["valid"] and r["mw"] > 0 for r in reactant_data])

if prod_mw and all_reactants_valid:
    # 1. Atom Economy (AE)
    sum_reactant_mw = sum(r["mw"] * r["coeff"] for r in reactant_data)
    ae = (prod_mw / sum_reactant_mw) * 100 if sum_reactant_mw > 0 else 0

    # 2. Reaction Mass Efficiency (RME)
    sum_reactant_mass = sum(r["mass"] for r in reactant_data)
    rme = (prod_mass / sum_reactant_mass) * 100 if sum_reactant_mass > 0 else 0

    # 3. Process Mass Intensity (PMI)
    total_input_mass = sum_reactant_mass + solvents_mass + reagents_mass + workup_mass + purification_mass
    pmi = total_input_mass / prod_mass if prod_mass > 0 else 0

    # 4. E-Factor
    total_waste = total_input_mass - prod_mass
    e_factor = total_waste / prod_mass if prod_mass > 0 else 0

    # 5. Carbon Efficiency (CE)
    prod_moles = prod_mass / prod_mw
    prod_carbon_moles = prod_moles * prod_c
    
    react_carbon_moles = sum((r["mass"] / r["mw"]) * r["c_count"] for r in reactant_data if r["mw"] > 0)
    ce = (prod_carbon_moles / react_carbon_moles) * 100 if react_carbon_moles > 0 else 0

    # Composite Green Score (0 to 100 scale heuristic)
    # AE & RME reward high %, PMI & Hazard penalize
    pmi_score = max(0, 100 - (pmi * 2))
    raw_green_score = (ae * 0.25) + (rme * 0.25) + (ce * 0.20) + (pmi_score * 0.30)
    final_green_score = max(0, min(100, raw_green_score / (1 + (hazard_penalty - 1) * 0.1)))

    # Metrics Display Cards
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Atom Economy", f"{ae:.1f}%")
    m2.metric("RME", f"{rme:.1f}%")
    m3.metric("Carbon Efficiency", f"{ce:.1f}%")
    m4.metric("PMI", f"{pmi:.2f}")
    m5.metric("E-Factor", f"{e_factor:.2f}")
    m6.metric("Green Score", f"{final_green_score:.1f} / 100")

    st.markdown("---")

    # Visualizations
    col_chart1, col_chart2 = st.columns([1, 1])

    with col_chart1:
        st.subheader("Mass Intensity Breakdown (PMI)")
        pmi_df = pd.DataFrame({
            "Category": ["Reactants", "Solvents", "Reagents/Catalysts", "Workup Materials", "Purification Media"],
            "Mass (g)": [sum_reactant_mass, solvents_mass, reagents_mass, workup_mass, purification_mass]
        })
        fig_pie = px.pie(pmi_df, values="Mass (g)", names="Category", title="Input Mass Distribution", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.subheader("Efficiency Summary")
        eff_df = pd.DataFrame({
            "Metric": ["Atom Economy", "Reaction Mass Efficiency", "Carbon Efficiency"],
            "Percentage (%)": [ae, rme, ce]
        })
        fig_bar = px.bar(eff_df, x="Metric", y="Percentage (%)", text_auto=".1f", color="Metric",
                         range_y=[0, 100], title="Chemical Yield & Material Utilization")
        st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.warning("Please enter valid SMILES strings for all products and reactants to calculate metrics.")
