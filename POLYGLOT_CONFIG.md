## Configuration

The Russound node server has the following user configuration parameters:

- IP Address       : The IP address of the ethernet to serial adaptor connected to the Russound
- Port             : Port used by the ethernet to serial adaptor
- Network Protocol : Either UDP or TCP
- Russound Protocol : Either RNET or RIO

** RIO only works with the TCP protocol.

Controllers that are chained via the RNET cable will be automatically detected and the zones/sources
on those controllers will be automatically set up.

Multiple controllers not chained can also be configured.
