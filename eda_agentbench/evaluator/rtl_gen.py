"""Compatibility shim: rtl_gen -> tb_sva_gen.

Old metadata may reference rtl_gen.RTLGenEvaluator. This module re-exports
TBSVAGenEvaluator under the old name so those references continue to work.
"""

from eda_agentbench.evaluator.tb_sva_gen import TBSVAGenEvaluator

RTLGenEvaluator = TBSVAGenEvaluator
