# Goodhart detector (eval harness)

Define a **divergence** metric between training reward and held-out evaluation. When divergence exceeds threshold **T** for **N** consecutive generations, flag for SPRT review.

This encodes structural detection of reward hacking (historical reference: G601–G810).
