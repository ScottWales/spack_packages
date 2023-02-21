from spack.package import *

class Yaxt(AutotoolsPackage):
    """
    Yet another exchange tool

    License: MIT
    """
    homepage = "https://swprojects.dkrz.de/redmine/projects/yaxt"
    url = "https://swprojects.dkrz.de/redmine/attachments/download/523/yaxt-0.9.3.1.tar.gz"

    maintainers = ['scottwales']

    version('0.9.3.1','5cc2ffeedf1604f825f22867753b637d41507941b7a0fbbfa6ea40637a77605a')

    depends_on('mpi')

    def install():
        env['CC'] = spec['mpi'].mpicc
        env['CXX'] = spec['mpi'].mpicxx
        env['F77'] = spec['mpi'].mpif77
        env['FC'] = spec['mpi'].mpifc
