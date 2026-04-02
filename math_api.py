import pulp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List

app = FastAPI(
    title="Navi Backend (Nivel 3 - Optimizer)",
    description="Microservicio matemático para integrarse con n8n y WhatsApp.",
    version="1.0.0"
)

# === ESQUEMAS DE DATOS (N8N enviará este JSON) ===
class Restriccion(BaseModel):
    nombre: str
    coeficientes: Dict[str, float]
    operador: str  # Solo usar: "<=", ">=", o "=="
    limite: float

class OptimizacionRequest(BaseModel):
    variables: List[str]
    tipo_optimizacion: str  # "maximizar" o "minimizar"
    funcion_objetivo: Dict[str, float]
    restricciones: List[Restriccion]

# === ENDPOINTS ===
@app.get("/")
def health_check():
    return {"estado": "El Servidor Matemático de Navi está corriendo perfectamente 🚀"}

@app.post("/optimizar")
def optimizar_modelo(req: OptimizacionRequest):
    """
    Endpoint principal. Recibe parámetros del Agente de n8n, 
    ejecuta el modelo matemático puro (PuLP) y devuelve resultados rígidos.
    """
    try:
        # 1. Definir sentido
        sentido = pulp.LpMaximize if req.tipo_optimizacion.lower() == "maximizar" else pulp.LpMinimize
        prob = pulp.LpProblem("Navi_Auto_Optimization", sentido)
        
        # 2. Instanciar variables (Enteros no negativos por defecto)
        vars_dict = {v: pulp.LpVariable(v, lowBound=0, cat='Integer') for v in req.variables}
        
        # 3. Función Objetivo
        prob += pulp.lpSum([req.funcion_objetivo.get(v, 0) * vars_dict[v] for v in req.variables]), "Objetivo"
        
        # 4. Restricciones
        for res in req.restricciones:
            expr = pulp.lpSum([res.coeficientes.get(v, 0) * vars_dict[v] for v in req.variables])
            if res.operador == "<=":
                prob += expr <= res.limite, res.nombre
            elif res.operador == ">=":
                prob += expr >= res.limite, res.nombre
            elif res.operador == "==":
                prob += expr == res.limite, res.nombre
                
        # 5. Ejecutar Solver Core
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        estado = pulp.LpStatus[prob.status]
        
        if estado == "Optimal":
            return {
                "success": True,
                "estado_matematico": estado,
                "valor_optimo": pulp.value(prob.objective),
                "plan_accion": {v.name: v.varValue for v in prob.variables()}
            }
        else:
            return {
                "success": False,
                "estado_matematico": estado,
                "error": "No se encontró solución factible dadas las restricciones comunicadas."
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falla en el motor matemático: {str(e)}")
