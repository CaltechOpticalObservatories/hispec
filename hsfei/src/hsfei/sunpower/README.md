# HSFEI

A collection of Python interfaces for communicating with HISPEC FEI components.

## Installation

```bash
pip install .
```

## Usage

```python
from hsfei import SunpowerController

controller = SunpowerController()
await controller.get_status()
```