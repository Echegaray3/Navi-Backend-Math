import pulp
import json
import sys
import os
import re
from typing import Dict, Any
from dotenv import load_dotenv

# Configurar salida en UTF-8 para soporte de emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Cargar variables de entorno desde .env local de la carpeta PoC_Solver
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

class LLMEngineer:
    """
    Agente LLM Real (Rol: Ingeniero de Investigación de Operaciones).
    Consume la API de OpenAI (GPT-4o-mini) con Structured Outputs (JSON Schema) y fallback robusto.
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def analizar_requisitos(self, prompt_negocio, custom_api_key=None):
        key_to_use = custom_api_key or self.api_key
        
        # JSON de contingencia local por defecto (Fallback determinista)
        fallback_json = {
            "variables": ["Sillas", "Mesas"],
            "tipo_optimizacion": "maximizar",
            "funcion_objetivo": {"Sillas": 20, "Mesas": 30},
            "restricciones": [
                {"nombre": "Madera", "coeficientes": {"Sillas": 1, "Mesas": 2}, "operador": "<=", "limite": 100},
                {"nombre": "Ensamblado", "coeficientes": {"Sillas": 3, "Mesas": 1}, "operador": "<=", "limite": 90}
            ]
        }

        if not key_to_use or not key_to_use.startswith("sk-"):
            print("[LLM Ingeniero - MODO SIMULADO]: No se detectó una OpenAI API Key válida. Activando contingencia local.")
            return fallback_json, "Simulado (Bypass Local - Sin API Key)"

        print("[LLM Ingeniero - MODO REAL]: Recibiendo requerimiento en lenguaje natural de negocios...")
        print(f"   Prompt Humano: '{prompt_negocio}'\n")

        try:
            import openai
            client = openai.OpenAI(api_key=key_to_use)
            
            # Llamada estructurada con validación estricta de esquema JSON
            # Para cumplir con la restricción "strict: true", estructuramos las propiedades dinámicas 
            # (como variables y restricciones) como listas de objetos variable-valor en lugar de diccionarios con llaves dinámicas.
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "Actúas como un Consultor Senior en Investigación de Operaciones e Ingeniero de Procesos Industriales. "
                            "Tu tarea es leer los requisitos de fabricación descritos en lenguaje natural por la gerencia y estructurarlos "
                            "matemáticamente. Extrae las variables de decisión, el tipo de optimización ('maximizar' o 'minimizar'), "
                            "los coeficientes de la función objetivo, y la lista de restricciones con sus coeficientes y límites físicos."
                        )
                    },
                    {"role": "user", "content": prompt_negocio}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "optimizacion_schema",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "variables": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Nombres únicos de las variables de decisión (ej. ['Sillas', 'Mesas'])"
                                },
                                "tipo_optimizacion": {
                                    "type": "string",
                                    "enum": ["maximizar", "minimizar"]
                                },
                                "funcion_objetivo": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "variable": {"type": "string", "description": "Nombre de la variable"},
                                            "valor": {"type": "number", "description": "Coeficiente económico de ganancia o costo"}
                                        },
                                        "required": ["variable", "valor"],
                                        "additionalProperties": False
                                    },
                                    "description": "Lista de coeficientes de la función objetivo para cada variable."
                                },
                                "restricciones": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "nombre": {"type": "string", "description": "Nombre del recurso o restricción, ej: 'Madera'"},
                                            "coeficientes": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "variable": {"type": "string", "description": "Nombre de la variable"},
                                                        "valor": {"type": "number", "description": "Coeficiente de uso de recurso"}
                                                    },
                                                    "required": ["variable", "valor"],
                                                    "additionalProperties": False
                                                }
                                            },
                                            "operador": {
                                                "type": "string",
                                                "enum": ["<=", ">=", "=="]
                                            },
                                            "limite": {"type": "number", "description": "Límite del lado derecho de la inecuación"}
                                        },
                                        "required": ["nombre", "coeficientes", "operador", "limite"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["variables", "tipo_optimizacion", "funcion_objetivo", "restricciones"],
                            "additionalProperties": False
                        }
                    }
                },
                temperature=0.0
            )
            
            result_text = response.choices[0].message.content
            parsed_json = json.loads(result_text)
            
            # Post-procesar para convertir listas a diccionarios compatibles con el Solver
            funcion_objetivo_dict = {item["variable"]: item["valor"] for item in parsed_json["funcion_objetivo"]}
            restricciones_procesadas = []
            for res in parsed_json["restricciones"]:
                coef_dict = {item["variable"]: item["valor"] for item in res["coeficientes"]}
                restricciones_procesadas.append({
                    "nombre": res["nombre"],
                    "coeficientes": coef_dict,
                    "operador": res["operador"],
                    "limite": res["limite"]
                })
            
            pulp_params = {
                "variables": parsed_json["variables"],
                "tipo_optimizacion": parsed_json["tipo_optimizacion"],
                "funcion_objetivo": funcion_objetivo_dict,
                "restricciones": restricciones_procesadas
            }
            
            print("[LLM Ingeniero - MODO REAL]: Requerimiento convertido con éxito a JSON estructurado usando GPT-4o-mini.")
            return pulp_params, "Real (OpenAI GPT-4o-mini)"
            
        except Exception as e:
            print(f"[LLM Ingeniero - FALLO API]: Error al conectar con OpenAI ({str(e)}). Activando bypass local resiliente.")
            return fallback_json, f"Simulado (Bypass Local - Fallo API: {type(e).__name__})"

    def interpretar_resultado(self, resultados_solver, custom_api_key=None):
        key_to_use = custom_api_key or self.api_key
        
        # Plantilla de contingencia determinista
        if resultados_solver['estado'] == 'Optimal':
            var_texts = ", ".join([f"{int(val)} {var}" for var, val in resultados_solver['variables'].items()])
            fallback_template = (
                f"Estimado Gerente, la decisión operativa óptima es producir: {var_texts}.\n"
                f"Con este plan, lograremos maximizar la utilidad hasta alcanzar ${int(resultados_solver['valor_objetivo'])} USD. "
                f"Este plan se calculó respetando estrictamente los límites de disponibilidad física en la planta."
            )
        else:
            fallback_template = "Atención: No existe una solución matemáticamente factible con los niveles de recursos actuales. Recomiendo evaluar la subcontratación o aumentar horas extra."

        if not key_to_use or not key_to_use.startswith("sk-"):
            return fallback_template

        try:
            import openai
            client = openai.OpenAI(api_key=key_to_use)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un Ingeniero en Investigación de Operaciones de una planta de manufactura inteligente. Tu tarea es tomar "
                            "los resultados numéricos crudos de un optimizador lineal de PuLP y redactar una respuesta formal, gerencial y "
                            "estructurada en español que resuma el plan óptimo y la utilidad total alcanzada de forma impecable y motivadora."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Resultados brutos del Solver:\n{json.dumps(resultados_solver, indent=2)}\n\n"
                            f"Redacta el informe breve para la gerencia interpretando estos datos."
                        )
                    }
                ],
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return fallback_template


class SolverExecutor:
    """
    Herramienta Analítica Autónoma (PULP Solver).
    Este módulo NO es IA (no alucina), usa algoritmos analíticos exactos (Branch & Cut / Simplex).
    """
    def resolver_milp(self, parametros):
        print("[Motor Matemático (Solver)]: Construyendo modelo MILP dinámicamente en Python...")
        
        # Validar Guardrail básico antes de compilar el modelo matemático
        if not parametros.get("variables") or not parametros.get("funcion_objetivo"):
            return {"estado": "Infeasible", "valor_objetivo": 0, "variables": {}}
            
        # Configurar Minimizar o Maximizar
        sentido = pulp.LpMaximize if parametros["tipo_optimizacion"] == "maximizar" else pulp.LpMinimize
        prob = pulp.LpProblem("Problema_Optimizacion_Empresarial", sentido)
        
        # 1. Variables de Decisión (Ej: Cantidades deben ser >= 0 e Enteras)
        vars_dict = {v: pulp.LpVariable(v, lowBound=0, cat='Integer') for v in parametros["variables"]}
        
        # 2. Función Objetivo
        prob += pulp.lpSum([parametros["funcion_objetivo"][v] * vars_dict[v] for v in parametros["variables"]]), "Beneficio_Total"
        
        # 3. Restricciones
        for res in parametros["restricciones"]:
            expr = pulp.lpSum([res["coeficientes"][v] * vars_dict[v] for v in parametros["variables"] if v in res["coeficientes"]])
            if res["operador"] == "<=":
                prob += expr <= res["limite"], res["nombre"]
            elif res["operador"] == ">=":
                prob += expr >= res["limite"], res["nombre"]
            elif res["operador"] == "==":
                prob += expr == res["limite"], res["nombre"]
                
        print("[Motor Matemático (Solver)]: Ejecutando algoritmo exacto (Branch & Cut)...")
        # Resolver usando el solver gratuito que viene con PuLP (CBC)
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        estado = pulp.LpStatus[prob.status]
        print(f"[Motor Matemático (Solver)]: Formulación exitosa. Resultado encontrado: {estado}")
        
        resultados = {
            "estado": estado,
            "valor_objetivo": pulp.value(prob.objective),
            "variables": {v.name: v.varValue for v in prob.variables()}
        }
        return resultados


# =============================================================================
# --- PARADIGMA COOPERATIVO NUBE-BORDE (ZOTERO CON EXTRACCIÓN REAL Y BYPASS) ---
# =============================================================================

class OperationalSolverTool:
    """
    Representa el Agente Cooperativo/Cognitivo que corre cerca de la planta (Edge).
    Ejecuta la optimización real basada en las directrices del LLM.
    Al correr localmente en el Borde, no alucina y asegura resultados físicos estrictos.
    """
    def execute_production_optimization(self, demand: int, available_hours: float) -> Dict[str, Any]:
        # Simulación de optimización matemática de asignación de recursos
        efficiency_factor = 0.85
        max_capacity = available_hours * 12 * efficiency_factor
        
        if demand <= max_capacity:
            status = "Óptimo alcanzado"
            allocated_resources = round(demand / (12 * efficiency_factor), 2)
            bottleneck = "Ninguno"
        else:
            status = "Capacidad insuficiente"
            allocated_resources = available_hours
            bottleneck = f"Déficit de {int(demand - max_capacity)} unidades"
            
        return {
            "status": status,
            "allocated_workers_needed": allocated_resources,
            "detected_bottleneck": bottleneck,
            "capacity_utilization_pct": round((demand / (available_hours * 12)) * 100, 2)
        }


class AutonomousManufacturingAgent:
    """
    Ecosistema del Agente en la Nube (Agentic AI).
    Posee las facultades cognitivas de interpretación, planificación y traducción conversacional.
    Usa la API de Anthropic Claude 3.5 Haiku para extracción y síntesis, con fallback a OpenAI GPT-4o-mini y Regex local.
    """
    def __init__(self, api_key=None):
        self.solver_tool = OperationalSolverTool()
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        
    def handle_strategic_request(self, user_prompt: str, plant_state: Dict[str, Any], custom_api_key: str = None):
        print(f"\n🤖 [Agentic AI - Nube]: Analizando petición estratégica: '{user_prompt}'")
        key_to_use = custom_api_key or self.api_key
        
        # 1. PASO DE RAZONAMIENTO Y GUARDRAIL SEMÁNTICO
        # Valores base de contingencia local
        target_demand = 500
        available_hours = plant_state.get("available_hours", 40.0)
        
        # Regex local de respaldo determinista
        numbers = re.findall(r'\d+', user_prompt)
        if len(numbers) >= 1:
            target_demand = int(numbers[1]) if "línea" in user_prompt.lower() and len(numbers) > 1 else int(numbers[0])
            
        modo = "Simulado (Bypass Local - Regex)"
        
        # Intentar extraer semánticamente con Anthropic Claude
        if key_to_use and key_to_use.startswith("sk-ant-"):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=key_to_use)
                
                # Usar Claude para extracción estructurada mediante Tool Calling
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1000,
                    temperature=0.0,
                    system=(
                        "Eres un asistente de Inteligencia Artificial especializado en planificación de capacidad industrial. "
                        "Tu tarea es analizar peticiones estratégicas de la gerencia y extraer con total precisión los parámetros de producción "
                        "requeridos para alimentar un solver matemático exacto de Borde. Debes ignorar palabras de ruido o números que representen "
                        "líneas de producción (ej. 'Línea 2') y capturar la demanda objetivo física real solicitada."
                    ),
                    messages=[
                        {"role": "user", "content": f"Extrae los parámetros operativos del siguiente prompt de gerencia: '{user_prompt}'"}
                    ],
                    tools=[
                        {
                            "name": "planificar_demanda",
                            "description": "Extrae los parámetros clave de la petición gerencial para planificar la capacidad de producción.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "demanda_objetivo": {
                                        "type": "integer",
                                        "description": "Número total de unidades demandadas. Ignora referencias a nombres de líneas (como línea 2) y quédate solo con la cantidad física del pedido."
                                    },
                                    "horas_disponibles": {
                                        "type": "number",
                                        "description": "Horas de turno disponibles si se mencionan en la petición, de lo contrario omitir o pasar null."
                                    }
                                },
                                "required": ["demanda_objetivo"]
                            }
                        }
                    ],
                    tool_choice={"type": "tool", "name": "planificar_demanda"}
                )
                
                # Extraer los datos del tool use
                tool_use = next(block for block in message.content if block.type == "tool_use")
                extracted_data = tool_use.input
                
                target_demand = extracted_data.get("demanda_objetivo", target_demand)
                if extracted_data.get("horas_disponibles") is not None:
                    available_hours = float(extracted_data["horas_disponibles"])
                
                modo = "Real (Anthropic Claude 3.5 Haiku)"
                print(f"[Agentic AI - Nube]: Extracción semántica exitosa usando Claude 3.5 Haiku.")
                
            except Exception as e:
                print(f"[Agentic AI - FALLO API ANTHROPIC]: Error al conectar con Anthropic ({str(e)}). Probando redundancia OpenAI.")
                modo = f"Falló Anthropic: {type(e).__name__}"

        # Resiliencia: si Anthropic falló o no está configurada, pero tenemos clave de OpenAI, usamos OpenAI
        if (not modo.startswith("Real")) and os.getenv("OPENAI_API_KEY"):
            try:
                print("[Agentic AI - Nube]: Activando extracción semántica redundante con OpenAI GPT-4o-mini...")
                import openai
                client_oa = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response_oa = client_oa.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un asistente de Inteligencia Artificial para manufactura industrial. Tu tarea es analizar "
                                "la petición del gerente y extraer la demanda objetivo (ignora referencias a nombres de líneas como 'Línea 2') "
                                "y las horas disponibles (si se mencionan, de lo contrario devuelve 0)."
                            )
                        },
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "demanda_schema",
                            "strict": True,
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "demanda_objetivo": {"type": "integer"},
                                    "horas_disponibles": {"type": "number"}
                                },
                                "required": ["demanda_objetivo", "horas_disponibles"],
                                "additionalProperties": False
                            }
                        }
                    },
                    temperature=0.0
                )
                res_oa = json.loads(response_oa.choices[0].message.content)
                target_demand = res_oa.get("demanda_objetivo", target_demand)
                if res_oa.get("horas_disponibles") is not None and res_oa["horas_disponibles"] > 0:
                    available_hours = float(res_oa["horas_disponibles"])
                
                modo = "Real (OpenAI GPT-4o-mini Fallback)"
                print(f"[Agentic AI - Nube]: Extracción semántica alternativa exitosa usando OpenAI.")
            except Exception as e_oa:
                print(f"[Agentic AI - FALLO MULTIPLE]: Ambos LLMs fallaron o están desconectados. Usando local regex.")
                modo = "Simulado (Bypass Local - Regex)"

        # Guardrail Físico Estricto antes de enviar al Solver del Edge
        if target_demand <= 0:
            return "⚠️ **Error de Planificación**: La demanda objetivo extraída no es válida físicamente para los sistemas de producción.", modo
            
        print("🔍 [Agentic AI - Nube]: Extrayendo parámetros para el Agente de Optimización de Borde...")
        print(f"   -> Demanda Objetivo: {target_demand} unidades.")
        print(f"   -> Horas Disponibles en Planta: {available_hours} h.")
        
        # 2. PASO DE ACCIÓN (Action / Tool Execution)
        print("⚙️ [Agente de Borde]: Ejecutando herramienta analítica exacta (sin alucinaciones)...")
        optimization_results = self.solver_tool.execute_production_optimization(
            demand=target_demand, 
            available_hours=available_hours
        )
        
        # 3. PASO DE EVALUACIÓN Y RESPUESTA (Conversational Synthesis)
        print("✍️ [Agentic AI - Nube]: Traduciendo matriz numérica a respuesta ejecutiva...")
        response = self._generate_conversational_response(user_prompt, optimization_results, key_to_use)
        return response, modo

    def _generate_conversational_response(self, prompt: str, results: Dict[str, Any], api_key: str = None) -> str:
        fallback_template = (
            f"✅ **Plan de Producción Optimizado**: La meta se puede cumplir con éxito.\n"
            f"• **Recursos a asignar**: Se requieren {results['allocated_workers_needed']} turnos equivalentes.\n"
            f"• **Estado**: {results['status']}.\n"
            f"• **Eficiencia esperada**: Estabilidad en el flujo sin cuellos de botella detectados."
        ) if "insuficiente" not in results["status"] else (
            f"⚠️ **Alerta de Planificación**: Tras evaluar su petición ('{prompt}'), "
            f"el optimizador del sistema detectó que la planta entrará en conflicto.\n"
            f"• **Problema**: {results['detected_bottleneck']}.\n"
            f"• **Uso de Capacidad**: El sistema intentó operar al {results['capacity_utilization_pct']}%.\n"
            f"• **Acción recomendada**: Es necesario autorizar horas extra o desviar parte de la carga de trabajo."
        )

        # Si tenemos Claude real, sintetizamos la respuesta de forma dinámica
        if api_key and api_key.startswith("sk-ant-"):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1000,
                    temperature=0.7,
                    system=(
                        "Eres un asistente ejecutivo de Inteligencia Artificial para plantas industriales. Tu rol es tomar la entrada del gerente "
                        "y los resultados numéricos puros de un optimizador matemático local para redactar una respuesta gerencial impecable, "
                        "concisa, bien estructurada, en español formal y usando emojis estratégicamente. Si hay capacidad insuficiente, explica "
                        "con empatía técnica y ofrece la acción recomendada de manera clara."
                    ),
                    messages=[
                        {
                            "role": "user", 
                            "content": (
                                f"Entrada del Gerente: '{prompt}'\n\n"
                                f"Resultados numéricos del solver matemático local del Borde:\n"
                                f"{json.dumps(results, indent=2)}\n\n"
                                f"Escribe la respuesta gerencial final interpretando estos datos de manera inteligente."
                            )
                        }
                    ]
                )
                return message.content[0].text.strip()
            except Exception:
                pass

        # Fallback alternativo a OpenAI para redactar la síntesis conversacional si Claude no está disponible
        if os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                client_oa = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                response_oa = client_oa.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un asistente ejecutivo de Inteligencia Artificial para plantas industriales. Tu rol es tomar la entrada del gerente "
                                "y los resultados numéricos de un optimizador matemático local para redactar una respuesta formal, gerencial y estructurada "
                                "en español usando emojis. Resalta el plan óptimo y recomendaciones."
                            )
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Entrada del Gerente: '{prompt}'\n\n"
                                f"Resultados numéricos:\n{json.dumps(results, indent=2)}"
                            )
                        }
                    ],
                    temperature=0.7
                )
                return response_oa.choices[0].message.content.strip()
            except Exception:
                pass

        # Si ambas APIs fallan o no están configuradas, se devuelve la plantilla local
        return fallback_template


# === FLUJO PRINCIPAL (ORQUESTADOR AUTONOMO - NIVEL 3 DUAL) ===
if __name__ == "__main__":
    print("\n=========================================================================")
    print("  FRAMEWORK TESIS DOCTORAL: ORQUESTADOR LLM + SOLVER MATEMATICO (NIVEL 3)")
    print("=========================================================================\n")
    
    print("Seleccione el paradigma de optimización a ejecutar:")
    print("1. Optimización Lineal Multivariable Clásica (PuLP + LLM - Sillas/Mesas)")
    print("2. Optimización Autónoma de Borde (Cloud-Edge Agentic AI - Articulo Zotero)")
    print("3. Ejecutar Ambos Paradigmas (Ejecución Comparativa)")
    
    opcion = input("\nIngrese su opción (1, 2 o 3): ").strip()
    if not opcion:
        opcion = "3"
        print(f"Opción no ingresada. Ejecutando opción {opcion} por defecto.")
    
    # --- PARADIGMA 1: MILP CLÁSICO ---
    if opcion in ["1", "3"]:
        print("\n-------------------------------------------------------------------------")
        print("  PARADIGMA 1: OPTIMIZACIÓN MULTIVARIABLE MILP (SILLAS & MESAS)")
        print("-------------------------------------------------------------------------")
        prompt_gerencial = (
            "Tenemos una fabrica. Cada Silla deja $20 USD de ganancia y cada Mesa $30 USD. "
            "Tenemos un limite de 100 kg de Madera y 90 horas de Ensamblado. "
            "La silla requiere 1 kg de madera y 3 horas, mientras que la mesa requiere 2 kg y 1 hora. "
            "¿Cuál es el mejor plan de producción?"
        )
        
        agente_llm = LLMEngineer()
        motor_solver = SolverExecutor()
        
        parametros_milp, modo = agente_llm.analizar_requisitos(prompt_gerencial)
        print(f"   [Modo de Extracción: {modo}]")
        
        resultado_matematico_bruto = motor_solver.resolver_milp(parametros_milp)
        decision_final = agente_llm.interpretar_resultado(resultado_matematico_bruto)
        
        print("\n======================== OUTPUT GERENCIAL (NIVEL 3) ========================")
        print(decision_final)
        print("============================================================================\n")

    # --- PARADIGMA 2: CLOUD-EDGE AGENTIC CO-OPERATIVE SYSTEM ---
    if opcion in ["2", "3"]:
        print("\n-------------------------------------------------------------------------")
        print("  PARADIGMA 2: COOPERACIÓN CLOUD-EDGE AGENTIC (ARTÍCULO ZOTERO)")
        print("-------------------------------------------------------------------------")
        
        current_edge_state = {
            "available_hours": 40.0,
            "active_machines": 5
        }
        
        agent_system = AutonomousManufacturingAgent()
        
        # Petición estratégica en lenguaje natural
        manager_query = "Necesito programar la producción para un pedido urgente de la línea 2 de 500 unidades."
        
        # Ejecución
        final_output, modo = agent_system.handle_strategic_request(manager_query, current_edge_state)
        print(f"   [Modo de Extracción: {modo}]")
        
        print("\n======================== OUTPUT GERENCIAL (ZOTERO) ========================")
        print(final_output)
        print("============================================================================\n")
