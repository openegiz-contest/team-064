# Environment notes

Official environment: https://openegiz-contest.github.io/environment/ (retrieved
for this revision). Ubuntu 24.04.5 amd64, 8 vCPU, 16 GiB RAM, 60 GB disk;
Docker Engine 29.1.3, Compose 2.40.3; 75-minute startup limit. `make` is not
preinstalled, so the README includes its installation. WebGL is supported but
rendering is software-based, without a GPU. Critical graphics files are bundled.

The authoring workspace is an extracted repository snapshot with no `.git`
directory. `git status` and `git fetch origin` therefore cannot inspect local
commits or organizer updates. No commits or pushes were made. Docker is not
installed here. The provided Stand verification must be run on the actual
integrated deployment; its result must not be inferred from local-mode tests.

Python model/API tests require only the standard library. Integrated startup
installs pinned paho-mqtt inside the Docker image. Optional Playwright browser
checks require their own developer tooling; they are not startup dependencies.
