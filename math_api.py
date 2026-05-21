import pulp
import os
import sys
import re
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Cargar variables de entorno
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Importar agentes de orquestador_poc directamente (ahora autónomo en el mismo directorio)
try:
    from orquestador_poc import LLMEngineer, SolverExecutor, AutonomousManufacturingAgent
except ImportError as e:
    print(f"Advertencia al importar agentes de orquestador_poc: {e}")

app = FastAPI(
    title="Navi Backend (Nivel 3 - Optimizer)",
    description="Microservicio matemático para integrarse con n8n y WhatsApp/Telegram.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    es_entero: bool = False # Nuevo campo para Branch & Bound

class TelegramRequest(BaseModel):
    mensaje: str
    available_hours: float = 40.0

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
        
        # 2. Instanciar variables (Soporta Continuas o Enteras)
        cat = pulp.LpInteger if req.es_entero else pulp.LpContinuous
        vars_dict = {v: pulp.LpVariable(v, lowBound=0, cat=cat) for v in req.variables}
        
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

@app.post("/telegram_optimizar")
def telegram_optimizar(req: TelegramRequest):
    """
    Endpoint de integración directa para Telegram y n8n.
    Recibe un mensaje en lenguaje natural, detecta el contexto del problema,
    ejecuta el agente cognitivo correspondiente + solver, y devuelve la respuesta
    redactada de forma ejecutiva lista para Telegram.
    """
    try:
        mensaje_lc = req.mensaje.lower()
        openai_key = os.getenv("OPENAI_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        
        # Auto-clasificación del problema
        is_milp = any(w in mensaje_lc for w in ["silla", "mesa", "madera", "milp", "ensamblado", "mueble"])
        
        if is_milp:
            # PARADIGMA 1: MILP Clásico
            agente_llm = LLMEngineer(api_key=openai_key)
            motor_solver = SolverExecutor()
            
            # Extraer y estructurar
            parametros_milp, modo = agente_llm.analizar_requisitos(req.mensaje, custom_api_key=openai_key)
            
            # Resolver
            resultado_matematico = motor_solver.resolver_milp(parametros_milp)
            
            # Sintetizar
            decision_final = agente_llm.interpretar_resultado(resultado_matematico, custom_api_key=openai_key)
            
            tipo_sol = "Éxito (Óptimo Global)" if resultado_matematico["estado"] == "Optimal" else "Inviable"
            emoji_sol = "✅" if resultado_matematico["estado"] == "Optimal" else "❌"
            
            respuesta_texto = (
                f"{emoji_sol} *[Smart Machine Orquestador - MILP]*\n"
                f"📊 *Estado:* `{tipo_sol}`\n"
                f"🔍 *Extracción:* `{modo}`\n"
                f"--------------------------------------------------\n\n"
                f"{decision_final}"
            )
        else:
            # PARADIGMA 2: Cloud-Edge (Zotero Capacity Planner)
            agent_system = AutonomousManufacturingAgent(api_key=anthropic_key)
            plant_state = {"available_hours": req.available_hours}
            
            # Ejecutar el flujo cognitivo-analítico
            decision_final, modo = agent_system.handle_strategic_request(req.mensaje, plant_state, custom_api_key=anthropic_key)
            
            # Detectar si hay déficit en la planta basándonos en la respuesta
            emoji_sol = "⚠️" if "capacidad insuficiente" in decision_final.lower() or "déficit" in decision_final.lower() else "🌐"
            
            respuesta_texto = (
                f"{emoji_sol} *[Smart Machine Orquestador - Cloud-Edge (Zotero)]*\n"
                f"🔍 *Extracción:* `{modo}`\n"
                f"--------------------------------------------------\n\n"
                f"{decision_final}"
            )
            
        return {"success": True, "respuesta": respuesta_texto}
        
    except Exception as e:
        return {"success": False, "respuesta": f"⚠️ *Error en el procesamiento del orquestador:* {str(e)}"}
