cmake_minimum_required(VERSION 3.28...3.31)
project(${SKBUILD_PROJECT_NAME} VERSION ${SKBUILD_PROJECT_VERSION} LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)   # static gemmi goes into a shared module

option(IBC_USE_SYSTEM_GEMMI "Use an installed gemmi (find_package) instead of fetching it" OFF)
set(IBC_GEMMI_VERSION "0.7.5" CACHE STRING "gemmi release to download when not using a system gemmi")

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

# ---------------------------------------------------------------- gemmi
if(IBC_USE_SYSTEM_GEMMI)
  find_package(gemmi CONFIG REQUIRED)
  message(STATUS "Using system gemmi ${gemmi_VERSION} from ${gemmi_DIR}")
else()
  message(STATUS "Fetching gemmi ${IBC_GEMMI_VERSION} (built as a static library)")
  set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
  set(USE_PYTHON OFF CACHE BOOL "" FORCE)
  include(FetchContent)
  FetchContent_Declare(
    gemmi
    URL https://github.com/project-gemmi/gemmi/archive/refs/tags/v${IBC_GEMMI_VERSION}.tar.gz
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    EXCLUDE_FROM_ALL            # build only gemmi_cpp, not gemmi's programs/tests
  )
  FetchContent_MakeAvailable(gemmi)
endif()

# ---------------------------------------------------------------- fast_mtz
pybind11_add_module(fast_mtz MODULE src/cpp/mtz_reader_py.cpp)
target_link_libraries(fast_mtz PRIVATE gemmi::gemmi_cpp)

find_package(OpenMP)
if(OpenMP_CXX_FOUND)
  target_link_libraries(fast_mtz PRIVATE OpenMP::OpenMP_CXX)
else()
  message(WARNING "OpenMP not found: fast_mtz will run single-threaded "
                  "(on macOS: `brew install libomp`).")
endif()

if(IBC_USE_SYSTEM_GEMMI)
  # A system gemmi may be a shared lib outside the default search path (e.g. ~/.local/lib).
  set_target_properties(fast_mtz PROPERTIES INSTALL_RPATH_USE_LINK_PATH TRUE)
endif()

# Installed inside the package: `from ibc import fast_mtz`.
install(TARGETS fast_mtz LIBRARY DESTINATION ibc COMPONENT python)
