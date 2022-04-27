# espy

<h1>Python API for ESP-r</h1>

Please note that these modules are primarily designed for my own use, and functions may change inputs or names without warning or concern for maintaining compatibility with any scripts you may have.

<h2>Install procedure</h2>

```bash
git clone https://github.com/johnallison0/espy.git
cd espy
python setup.py install
```

<h2>Structure</h2>

ESPy is broken up into modules. Many of these echo names of ESP-r modules (e.g. bps, res, clm), that contain functions to automate functionality of these modules. Other modules contain various support facilities, as well as functions for interacting with ESP-r models without using the ESP-r interface.

For full namespace documentation, refer to the ./doc directory.

<h2>Usage</h2>

If the installation procedure above was followed, then ESPy modules should be included in Python code in the same manner as any other installed modules. A minimal workflow for a typical simulation and results extraction task might be the following:

```python
import espy.bps as bps
from espy.res import time_series

bps.run_preset('./cfg/model.cfg','annual')
time_series('./cfg/model.cfg','annual.res',[['all', 'Zone db T']],'res.csv')
```

You would then have dry bulb temperature for all zones, in file res.csv. Alternatively, you could work with a DataFrame of the results:

```python
import pandas as pd
from espy.res import time_series

res_df = time_series('./cfg/model.cfg','annual.res',[['all', 'Zone db T']])
res_df['Zone1_dbT'].to_csv('Zone1res.csv')
```

There are many other functions provided by ESPy. For full documentation, refer to the ./doc directory.


