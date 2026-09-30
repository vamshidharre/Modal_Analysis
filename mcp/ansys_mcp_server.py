#!/usr/bin/env python3
"""
Ansys MCP Server
A Model Context Protocol server for interfacing with Ansys simulation software.
Supports Ansys Mechanical, Fluent, MAPDL, and file operations.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union
import json
from pathlib import Path

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ansys-mcp")


class AnsysInterface:
    """Interface for Ansys operations"""

    def __init__(self):
        # Auto-detect Ansys root path: check ANSYS_ROOT, then scan for AWP_ROOT* env vars
        self.ansys_path = os.environ.get('ANSYS_ROOT', '')
        if not self.ansys_path:
            for k in sorted(os.environ.keys(), reverse=True):
                if k.startswith('AWP_ROOT') and os.environ.get(k):
                    self.ansys_path = os.environ[k]
                    break

        self.working_directory = Path.cwd() / "ansys_work"
        self.working_directory.mkdir(exist_ok=True)

        # Active session store
        self.fluent_sessions: Dict[str, Any] = {}
        self.mapdl_sessions: Dict[str, Any] = {}
        self.mechanical_sessions: Dict[str, Any] = {}

    def check_ansys_installation(self) -> Dict[str, Any]:
        """Check if Ansys is installed and accessible"""
        try:
            available_modules = {}

            # Check Fluent
            try:
                import ansys.fluent.core as pyfluent
                available_modules['fluent'] = True
            except ImportError:
                available_modules['fluent'] = False

            # Check MAPDL
            try:
                import ansys.mapdl.core as pymapdl
                available_modules['mapdl'] = True
            except ImportError:
                available_modules['mapdl'] = False

            # Check Mechanical
            try:
                import ansys.mechanical.core as pymech
                available_modules['mechanical'] = True
            except ImportError:
                available_modules['mechanical'] = False

            # Check Geometry
            try:
                import ansys.geometry.core as pyansys_geometry
                available_modules['geometry'] = True
            except ImportError:
                available_modules['geometry'] = False

            return {
                "status": "available" if any(available_modules.values()) else "not_found",
                "modules": available_modules,
                "ansys_path": self.ansys_path,
                "working_directory": str(self.working_directory),
                "active_sessions": {
                    "fluent": len(self.fluent_sessions),
                    "mapdl": len(self.mapdl_sessions),
                    "mechanical": len(self.mechanical_sessions)
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------ Mechanical Operations ------------------

    async def create_mechanical_session(self, version: Optional[int] = None, port: Optional[int] = None, show_gui: bool = False) -> Dict[str, Any]:
        """Launch a new Mechanical session via PyMechanical"""
        try:
            import ansys.mechanical.core as pymech

            kwargs = {}
            if version:
                kwargs["version"] = version
            if port:
                kwargs["port"] = port
            if show_gui:
                kwargs["batch"] = False

            mech = pymech.launch_mechanical(**kwargs)
            session_id = str(id(mech))
            self.mechanical_sessions[session_id] = mech

            return {
                "status": "success",
                "session_id": session_id,
                "version": getattr(mech, 'version', None),
                "project_directory": getattr(mech, 'project_directory', None)
            }
        except ImportError:
            return {"status": "error", "message": "PyMechanical (ansys-mechanical-core) not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def connect_to_mechanical(self, port: int, ip: str = "localhost") -> Dict[str, Any]:
        """Connect to an existing running Mechanical instance on a gRPC port"""
        try:
            import ansys.mechanical.core as pymech

            mech = pymech.connect_to_mechanical(ip=ip, port=port)
            session_id = str(id(mech))
            self.mechanical_sessions[session_id] = mech

            return {
                "status": "success",
                "session_id": session_id,
                "version": getattr(mech, 'version', None),
                "project_directory": getattr(mech, 'project_directory', None)
            }
        except ImportError:
            return {"status": "error", "message": "PyMechanical not installed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def run_mechanical_script(self, script: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a Python/IronPython script in Mechanical"""
        try:
            if not self.mechanical_sessions:
                return {"status": "error", "message": "No active Mechanical session. Call create_mechanical_session or connect_to_mechanical first."}

            mech = self.mechanical_sessions.get(session_id) if session_id else list(self.mechanical_sessions.values())[-1]
            if not mech:
                return {"status": "error", "message": f"Mechanical session {session_id} not found"}

            output = mech.run_python_script(script)
            return {
                "status": "success",
                "output": str(output)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------ Fluent Operations ------------------

    async def create_fluent_session(self, precision: str = "double",
                                    dimension: str = "3d",
                                    show_gui: bool = False) -> Dict[str, Any]:
        """Create a new Fluent session"""
        try:
            import ansys.fluent.core as pyfluent

            kwargs = {
                "precision": precision,
                "dimension": dimension,
                "mode": "solver"
            }
            if show_gui:
                kwargs["ui_mode"] = "gui"

            session = pyfluent.launch_fluent(**kwargs)
            session_id = str(id(session))
            self.fluent_sessions[session_id] = session

            return {
                "status": "success",
                "session_id": session_id,
                "precision": precision,
                "dimension": dimension
            }
        except ImportError:
            return {"status": "error", "message": "PyFluent (ansys-fluent-core) not available"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def connect_to_fluent(self, port: int, ip: str = "localhost") -> Dict[str, Any]:
        """Connect to an existing running Fluent instance with active server/gRPC port"""
        try:
            import ansys.fluent.core as pyfluent

            session = pyfluent.connect_to_fluent(ip=ip, port=port)
            session_id = str(id(session))
            self.fluent_sessions[session_id] = session

            return {
                "status": "success",
                "session_id": session_id,
                "ip": ip,
                "port": port
            }
        except ImportError:
            return {"status": "error", "message": "PyFluent not available"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def run_fluent_commands(self, commands: List[str], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute Fluent TUI commands"""
        try:
            if not self.fluent_sessions:
                return {"status": "error", "message": "No active Fluent session. Call create_fluent_session or connect_to_fluent first."}

            session = self.fluent_sessions.get(session_id) if session_id else list(self.fluent_sessions.values())[-1]
            if not session:
                return {"status": "error", "message": f"Fluent session {session_id} not found"}

            results = []
            for cmd in commands:
                out = session.tui(cmd)
                results.append({
                    "command": cmd,
                    "status": "executed",
                    "output": str(out)
                })

            return {
                "status": "success",
                "commands_executed": len(commands),
                "results": results
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------ MAPDL Operations ------------------

    async def create_mapdl_session(self, run_location: Optional[str] = None) -> Dict[str, Any]:
        """Create a new MAPDL session"""
        try:
            import ansys.mapdl.core as pymapdl

            mapdl = pymapdl.launch_mapdl(
                run_location=run_location or str(self.working_directory)
            )
            session_id = str(id(mapdl))
            self.mapdl_sessions[session_id] = mapdl

            return {
                "status": "success",
                "session_id": session_id,
                "version": getattr(mapdl, 'version', None),
                "run_location": getattr(mapdl, 'directory', None)
            }
        except ImportError:
            return {"status": "error", "message": "PyMAPDL (ansys-mapdl-core) not available"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def run_mapdl_commands(self, commands: List[str], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute MAPDL commands"""
        try:
            if not self.mapdl_sessions:
                return {"status": "error", "message": "No active MAPDL session. Call create_mapdl_session first."}

            mapdl = self.mapdl_sessions.get(session_id) if session_id else list(self.mapdl_sessions.values())[-1]
            if not mapdl:
                return {"status": "error", "message": f"MAPDL session {session_id} not found"}

            results = []
            for cmd in commands:
                out = mapdl.run(cmd)
                results.append({
                    "command": cmd,
                    "status": "executed",
                    "output": str(out)
                })

            return {
                "status": "success",
                "commands_executed": len(commands),
                "results": results
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------ File Operations ------------------

    async def read_ansys_file(self, file_path: str) -> Dict[str, Any]:
        """Read and inspect various Ansys file formats"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"status": "error", "message": f"File not found: {file_path}"}

            ext = path.suffix.lower()
            file_info = {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "extension": ext
            }

            # Map extensions
            file_types = {
                '.cas': "Fluent case file",
                '.dat': "Fluent/Ansys data file",
                '.h5': "Ansys HDF5 file (Fluent/Mechanical)",
                '.inp': "MAPDL input file",
                '.cdb': "MAPDL blocked database file",
                '.rst': "MAPDL structural result file",
                '.rth': "MAPDL thermal result file",
                '.wbpj': "Ansys Workbench project file",
                '.wbdp': "Ansys Workbench design point file",
                '.engd': "Ansys Engineering Data file",
                '.mechdat': "Ansys Mechanical project archive",
                '.agdb': "Ansys DesignModeler geometry file",
                '.scdoc': "Ansys SpaceClaim document",
                '.scdocx': "Ansys SpaceClaim document"
            }
            file_info["type"] = file_types.get(ext, "Unknown / custom Ansys file")

            # For text/XML files, read a preview
            if ext in ['.inp', '.jou', '.xml', '.engd', '.dat', '.txt', '.py']:
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_info["preview"] = f.read(1500)
                except Exception:
                    pass

            return {"status": "success", "file_info": file_info}

        except Exception as e:
            return {"status": "error", "message": str(e)}


# Initialize Ansys interface
ansys_interface = AnsysInterface()

# Create the MCP server
server = Server("ansys-mcp")


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available Ansys resources"""
    return [
        Resource(
            uri="ansys://status",
            name="Ansys Installation Status",
            description="Check Ansys installation and available modules",
            mimeType="application/json",
        ),
        Resource(
            uri="ansys://working-directory",
            name="Working Directory",
            description="Current Ansys working directory and files",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read Ansys resources"""
    if uri == "ansys://status":
        status = ansys_interface.check_ansys_installation()
        return json.dumps(status, indent=2)

    elif uri == "ansys://working-directory":
        work_dir = ansys_interface.working_directory
        files = []
        if work_dir.exists():
            for file in work_dir.iterdir():
                if file.is_file():
                    files.append({
                        "name": file.name,
                        "size": file.stat().st_size,
                        "modified": file.stat().st_mtime
                    })

        return json.dumps({
            "directory": str(work_dir),
            "files": files
        }, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available Ansys tools"""
    return [
        Tool(
            name="check_ansys_status",
            description="Check Ansys installation status, root path, and available modules (Mechanical, Fluent, MAPDL, Geometry)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="create_mechanical_session",
            description="Launch a new Ansys Mechanical session via PyMechanical (optionally with GUI visible)",
            inputSchema={
                "type": "object",
                "properties": {
                    "show_gui": {
                        "type": "boolean",
                        "description": "True to show Mechanical window GUI, False for background headless mode (default: False)"
                    },
                    "version": {
                        "type": "integer",
                        "description": "Ansys version number (e.g., 261 for 2026 R1)"
                    },
                    "port": {
                        "type": "integer",
                        "description": "gRPC communication port (optional)"
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="connect_to_mechanical",
            description="Connect to an already running Ansys Mechanical instance on a specified gRPC port",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "description": "gRPC communication port of running Mechanical instance"
                    },
                    "ip": {
                        "type": "string",
                        "default": "localhost",
                        "description": "Host IP (default: localhost)"
                    }
                },
                "required": ["port"],
            },
        ),
        Tool(
            name="run_mechanical_script",
            description="Execute Python or IronPython automation script within an active Ansys Mechanical session",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Python/IronPython script commands to execute in Mechanical"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Target Mechanical session ID (optional, defaults to latest session)"
                    }
                },
                "required": ["script"],
            },
        ),
        Tool(
            name="create_fluent_session",
            description="Launch a new Ansys Fluent simulation session via PyFluent",
            inputSchema={
                "type": "object",
                "properties": {
                    "show_gui": {
                        "type": "boolean",
                        "description": "True to launch Fluent with GUI window visible (default: False)"
                    },
                    "precision": {
                        "type": "string",
                        "enum": ["single", "double"],
                        "default": "double",
                        "description": "Calculation precision"
                    },
                    "dimension": {
                        "type": "string",
                        "enum": ["2d", "3d"],
                        "default": "3d",
                        "description": "Simulation dimension"
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="connect_to_fluent",
            description="Connect to an already running Ansys Fluent instance with server/gRPC port active",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {
                        "type": "integer",
                        "description": "Port number of the running Fluent server session"
                    },
                    "ip": {
                        "type": "string",
                        "default": "localhost",
                        "description": "Host IP (default: localhost)"
                    }
                },
                "required": ["port"],
            },
        ),
        Tool(
            name="run_fluent_commands",
            description="Execute TUI commands in an active Fluent session",
            inputSchema={
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of Fluent TUI commands to execute"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Target Fluent session ID (optional, defaults to latest session)"
                    }
                },
                "required": ["commands"],
            },
        ),
        Tool(
            name="create_mapdl_session",
            description="Create a new Ansys MAPDL (FEA) session via PyMAPDL",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_location": {
                        "type": "string",
                        "description": "Directory to run MAPDL working files (optional)"
                    }
                },
                "required": [],
            },
        ),
        Tool(
            name="run_mapdl_commands",
            description="Execute APDL commands in an active MAPDL session",
            inputSchema={
                "type": "object",
                "properties": {
                    "commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of APDL commands to execute"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Target MAPDL session ID (optional, defaults to latest session)"
                    }
                },
                "required": ["commands"],
            },
        ),
        Tool(
            name="read_ansys_file",
            description="Read, inspect, and analyze Ansys files (.cas, .dat, .inp, .rst, .wbpj, .engd, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute or relative path to the Ansys file"
                    }
                },
                "required": ["file_path"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Handle tool calls"""
    if arguments is None:
        arguments = {}

    try:
        if name == "check_ansys_status":
            result = ansys_interface.check_ansys_installation()

        elif name == "create_mechanical_session":
            result = await ansys_interface.create_mechanical_session(
                version=arguments.get("version"),
                port=arguments.get("port"),
                show_gui=arguments.get("show_gui", False)
            )

        elif name == "connect_to_mechanical":
            result = await ansys_interface.connect_to_mechanical(
                port=arguments["port"],
                ip=arguments.get("ip", "localhost")
            )

        elif name == "run_mechanical_script":
            result = await ansys_interface.run_mechanical_script(
                script=arguments["script"],
                session_id=arguments.get("session_id")
            )

        elif name == "create_fluent_session":
            result = await ansys_interface.create_fluent_session(
                precision=arguments.get("precision", "double"),
                dimension=arguments.get("dimension", "3d"),
                show_gui=arguments.get("show_gui", False)
            )

        elif name == "connect_to_fluent":
            result = await ansys_interface.connect_to_fluent(
                port=arguments["port"],
                ip=arguments.get("ip", "localhost")
            )

        elif name == "run_fluent_commands":
            result = await ansys_interface.run_fluent_commands(
                commands=arguments["commands"],
                session_id=arguments.get("session_id")
            )

        elif name == "create_mapdl_session":
            result = await ansys_interface.create_mapdl_session(
                run_location=arguments.get("run_location")
            )

        elif name == "run_mapdl_commands":
            result = await ansys_interface.run_mapdl_commands(
                commands=arguments["commands"],
                session_id=arguments.get("session_id")
            )

        elif name == "read_ansys_file":
            result = await ansys_interface.read_ansys_file(
                file_path=arguments["file_path"]
            )

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        error_result = {"status": "error", "message": str(e)}
        return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def main():
    """Main entry point"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ansys-mcp",
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())