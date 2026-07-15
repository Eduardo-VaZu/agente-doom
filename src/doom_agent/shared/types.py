from pathlib import Path
from typing import TypeAlias

import numpy as np
from numpy.typing import NDArray

PathLike: TypeAlias = str | Path
Observation: TypeAlias = NDArray[np.uint8]
DictObservation: TypeAlias = dict[str, np.ndarray]
BinaryAction: TypeAlias = NDArray[np.int32]
AgentAction: TypeAlias = int | NDArray[np.int32] | NDArray[np.int64]
