# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# Copyright 2023 ACCESS-NRI
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack.package import install, join_path, mkdirp

# https://spack.readthedocs.io/en/latest/build_systems/makefilepackage.html
class Cice5(MakefilePackage):
    """The Los Alamos sea ice model (CICE) is the result of an effort to develop a computationally efficient sea ice component for a fully coupled atmosphere-land global climate model."""

    homepage = "https://www.access-nri.org.au"
    git = "https://github.com/ACCESS-NRI/cice5.git"
    # NOTE: URL definition required for CI
    # Spack needs tarball URL to be defined to access github branches
    url = "https://github.com/ACCESS-NRI/cice5/tarball/master"

    maintainers = ["harshula"]

    version("master", branch="master")

    # Depend on virtual package "mpi".
    depends_on("mpi")
    depends_on("oasis3-mct")
    depends_on("datetime-fortran")
    depends_on("netcdf-fortran@4.5.2:")
    depends_on("netcdf-c@4.7.4:")
    # TODO: For initial verification we are going to use static pio.
    #       Eventually we plan to move to shared pio
    # ~shared requires: https://github.com/spack/spack/pull/34837
    depends_on("parallelio~pnetcdf~timing~shared")
    depends_on("libaccessom2")

    phases = ["edit", "build", "install"]

    _buildscript = "spack-build.sh"
    _buildscript_path = join_path("bld", _buildscript)

    # The integer represents environment variable NTASK
    __targets = {24: {}, 480: {}, 722: {}, 1682: {}}
    __targets[24]["driver"] = "auscom"
    __targets[24]["grid"] = "360x300"
    __targets[24]["blocks"] = "24x1"

    __targets[480]["driver"] = "auscom"
    __targets[480]["grid"] = "1440x1080"
    __targets[480]["blocks"] = "48x40"

    # Comment from bld/config.nci.auscom.3600x2700:
    # Recommendations:
    #   use processor_shape = slenderX1 or slenderX2 in ice_in
    #   one per processor with distribution_type='cartesian' or
    #   squarish blocks with distribution_type='rake'
    # If BLCKX (BLCKY) does not divide NXGLOB (NYGLOB) evenly, padding
    # will be used on the right (top) of the grid.
    __targets[722]["driver"] = "auscom"
    __targets[722]["grid"] = "3600x2700"
    __targets[722]["blocks"] = "90x90"

    __targets[1682]["driver"] = "auscom"
    __targets[1682]["grid"] = "3600x2700"
    __targets[1682]["blocks"] = "200x180"

    def edit(self, spec, prefix):

        srcdir = self.stage.source_path
        buildscript_dest = join_path(srcdir, self._buildscript_path)
        makeinc_path = join_path(srcdir, "bld", "Macros.spack")

        copy(join_path(self.package_dir, self._buildscript), buildscript_dest)

        config = {}

        istr = join_path((spec["oasis3-mct"].headers).cpp_flags, "psmile.MPI1")
        ideps = ["parallelio", "oasis3-mct", "libaccessom2", "netcdf-fortran"]
        incs = " ".join([istr] + [(spec[d].headers).cpp_flags for d in ideps])

        lstr = " ".join(
                    ["-L" + join_path(spec["parallelio"].prefix, "lib"),
                    "-lpiof",
                    "-lpioc"]
                   )
        # NOTE: The order of the libraries matter during the linking step!
        # NOTE: datetime-fortran is a dependency of libaccessom2.
        ldeps = ["oasis3-mct", "libaccessom2", "netcdf-c", "netcdf-fortran", "datetime-fortran"]
        libs = " ".join([lstr] + [(spec[d].libs).ld_flags for d in ldeps])

        # Copied from bld/Macros.nci
        config["pre"] = f"""
INCLDIR    := -I. {incs}
SLIBS      := {libs}
ULIBS      :=
CPP        := cpp
FC         := mpifort

CPPFLAGS   := -P -traditional
CPPDEFS    := -DLINUX -DPAROPT
CFLAGS     := -c -O2
FIXEDFLAGS := -132
FREEFLAGS  :=
"""

        config["gcc"] = f"""
# TODO: removed -std=f2008 due to compiler errors
FFLAGS = -Wall -fdefault-real-8 -fdefault-double-8 -ffpe-trap=invalid,zero,overflow -fallow-argument-mismatch
"""

        # module load intel-compiler/2019.5.281
        config["intel"] = f"""
NCI_INTEL_FLAGS := -r8 -i4 -traceback -w -fpe0 -ftz -convert big_endian -assume byterecl -check noarg_temp_created
NCI_REPRO_FLAGS := -fp-model precise -fp-model source -align all
ifeq ($(DEBUG), 1)
    NCI_DEBUG_FLAGS := -g3 -O0 -debug all -check all -no-vec -assume nobuffered_io
    FFLAGS          := $(NCI_INTEL_FLAGS) $(NCI_REPRO_FLAGS) $(NCI_DEBUG_FLAGS)
    CPPDEFS         := $(CPPDEFS) -DDEBUG=$(DEBUG)
else
    NCI_OPTIM_FLAGS := -g3 -O2 -axCORE-AVX2 -debug all -check none -qopt-report=5 -qopt-report-annotate -assume buffered_io
    FFLAGS          := $(NCI_INTEL_FLAGS) $(NCI_REPRO_FLAGS) $(NCI_OPTIM_FLAGS)
endif
"""

        # Copied from bld/Macros.nci
        config["post"] = """
MOD_SUFFIX := mod
LD         := $(FC)
LDFLAGS    := $(FFLAGS) -v

CPPDEFS :=  $(CPPDEFS) -DNXGLOB=$(NXGLOB) -DNYGLOB=$(NYGLOB) \
            -DNUMIN=$(NUMIN) -DNUMAX=$(NUMAX) \
            -DTRAGE=$(TRAGE) -DTRFY=$(TRFY) -DTRLVL=$(TRLVL) \
            -DTRPND=$(TRPND) -DNTRAERO=$(NTRAERO) -DTRBRI=$(TRBRI) \
            -DNBGCLYR=$(NBGCLYR) -DTRBGCS=$(TRBGCS) \
            -DNICECAT=$(NICECAT) -DNICELYR=$(NICELYR) \
            -DNSNWLYR=$(NSNWLYR) \
            -DBLCKX=$(BLCKX) -DBLCKY=$(BLCKY) -DMXBLCKS=$(MXBLCKS)

ifeq ($(COMMDIR), mpi)
   SLIBS   :=  $(SLIBS) -lmpi
endif

ifeq ($(DITTO), yes)
   CPPDEFS :=  $(CPPDEFS) -DREPRODUCIBLE
endif
ifeq ($(BARRIERS), yes)
   CPPDEFS :=  $(CPPDEFS) -Dgather_scatter_barrier
endif

ifeq ($(IO_TYPE), netcdf)
   CPPDEFS :=  $(CPPDEFS) -Dncdf
endif

ifeq ($(IO_TYPE), pio)
   CPPDEFS :=  $(CPPDEFS) -Dncdf -DPIO
endif

# TODO: Do we want to delete this conditional?
#ifeq ($(USE_ESMF), yes)
#   CPPDEFS :=  $(CPPDEFS) -Duse_esmf
#   INCLDIR :=  $(INCLDIR) -I ???
#   SLIBS   :=  $(SLIBS) -L ??? -lesmf -lcprts -lrt -ldl
#endif

ifeq ($(AusCOM), yes)
   CPPDEFS := $(CPPDEFS) -DAusCOM -Dcoupled
endif

ifeq ($(UNIT_TESTING), yes)
   CPPDEFS := $(CPPDEFS) -DUNIT_TESTING
endif
ifeq ($(ACCESS), yes)
   CPPDEFS := $(CPPDEFS) -DACCESS
endif
# standalone CICE with AusCOM mods
ifeq ($(ACCICE), yes)
   CPPDEFS := $(CPPDEFS) -DACCICE
endif
# no MOM just CICE+UM
ifeq ($(NOMOM), yes)
   CPPDEFS := $(CPPDEFS) -DNOMOM
endif
ifeq ($(OASIS3_MCT), yes)
   CPPDEFS := $(CPPDEFS) -DOASIS3_MCT
endif
"""
        with open(makeinc_path, "w") as makeinc:
            makeinc.write(
                config["pre"]
                + config[self.compiler.name]
                + config["post"]
            )

    def build(self, spec, prefix):

        build = Executable(
                    join_path(self.stage.source_path, self._buildscript_path)
                )

        for k in self.__targets:
            build(self.__targets[k]["driver"],
                    self.__targets[k]["grid"],
                    self.__targets[k]["blocks"],
                    str(k))

    def install(self, spec, prefix):

        mkdirp(prefix.bin)
        for k in self.__targets:
            name = "_".join([self.__targets[k]["driver"],
                                self.__targets[k]["grid"],
                                self.__targets[k]["blocks"],
                                str(k) + "p"])
            install(join_path("build_" + name, "cice_" + name + ".exe"),
                    prefix.bin)
