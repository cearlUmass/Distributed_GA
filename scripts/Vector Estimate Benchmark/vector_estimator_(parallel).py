from DGA.Server import Server
from DGA.Model import Testing_Model as Model    # Vector estimation model
from DGA.Gene import Gene, Genome
from DGA.Algorithm import Genetic_Algorithm as Algorithm

if __name__ == '__main__':
  # Run variables
  VECTOR_SHAPE = (10, 10)

  genome = Genome()
  gene = Gene(shape=VECTOR_SHAPE, dtype=float, min_val=-10, max_val=10)
  genome.add_gene(gene, 'vector_gene')

  mod = Model(genome=genome, vector_size=VECTOR_SHAPE, vector_distribution=10, vector_scale=3)
  alg = Algorithm(num_params=10, iterations=1_000, genome=genome, num_parents=2)
  sync_runner = Server(run_name="Vect-Est (parallel)", algorithm=alg, model=mod, num_parallel_processes=10)
