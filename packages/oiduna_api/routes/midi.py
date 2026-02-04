"""GET/POST /midi/* - MIDI device management endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from oiduna_api.services.loop_service import LoopService, get_loop_service

router = APIRouter()


class MidiPort(BaseModel):
    """MIDI port information"""

    name: str
    is_input: bool
    is_output: bool


class MidiPortsResponse(BaseModel):
    """Response listing available MIDI ports"""

    ports: list[MidiPort]


class SelectPortRequest(BaseModel):
    """Request to select a MIDI port"""

    port_name: str = Field(..., description="Name of the MIDI port to select")


class SelectPortResponse(BaseModel):
    """Response after selecting MIDI port"""

    status: str
    port_name: str


class PanicResponse(BaseModel):
    """Response after MIDI panic (all notes off)"""

    status: str


@router.get("/ports", response_model=MidiPortsResponse)
async def list_midi_ports(
    loop_service: LoopService = Depends(get_loop_service),
) -> MidiPortsResponse:
    """List all available MIDI input/output ports"""
    try:
        import mido

        ports: list[MidiPort] = []

        # Get input ports
        for name in mido.get_input_names():
            ports.append(MidiPort(name=name, is_input=True, is_output=False))

        # Get output ports
        for name in mido.get_output_names():
            ports.append(MidiPort(name=name, is_input=False, is_output=True))

        return MidiPortsResponse(ports=ports)

    except ImportError:
        raise HTTPException(
            status_code=500, detail="MIDI support not available (mido not installed)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list MIDI ports: {e!s}")


@router.post("/port", response_model=SelectPortResponse)
async def select_midi_port(
    req: SelectPortRequest,
    loop_service: LoopService = Depends(get_loop_service),
) -> SelectPortResponse:
    """Select a MIDI output port for sending MIDI messages"""
    try:
        engine = loop_service.get_engine()
        # BUG FIX: Use "port_name" instead of "port"
        result = engine._handle_midi_port({"port_name": req.port_name})

        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)

        return SelectPortResponse(status="ok", port_name=req.port_name)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select MIDI port: {e!s}")


@router.post("/panic", response_model=PanicResponse)
async def midi_panic(
    loop_service: LoopService = Depends(get_loop_service),
) -> PanicResponse:
    """Send all notes off message on all MIDI channels"""
    try:
        engine = loop_service.get_engine()
        result = engine._handle_midi_panic({})

        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)

        return PanicResponse(status="ok")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send MIDI panic: {e!s}")
