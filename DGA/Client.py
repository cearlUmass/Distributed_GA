from abc import abstractmethod
from DGA.pool_functions import load_gene

POOL_DIR = "pool"
LOCK_DIR = "locks"


class Client():
  def __init__(self, run_name: str, gene_name: str):
    self.run_name = run_name
    self.gene_name = gene_name
    self.gene_data = load_gene(gene_name, run_name)   # Note: Read should be safe as long as only 1 client runs gene

  # Run model
  @abstractmethod
  def run(self) -> float:
    pass