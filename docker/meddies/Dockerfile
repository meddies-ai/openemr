# meddies/openemr:7.0.3-patched
#
# Layers the meddies timing.repeat patch on top of the upstream
# openemr/openemr:7.0.3 image. The patched file replaces
# /var/www/localhost/htdocs/openemr/src/Services/FHIR/FhirMedicationRequestService.php
# inside the container.
#
# Why this lives here:
#   - The fork's `src/Services/FHIR/FhirMedicationRequestService.php` (master HEAD)
#     has a completely different file shape than v7.0.3 — the upstream code was
#     refactored after this release. The runtime patch (this file) is shaped for
#     v7.0.3; the upstream-PR patch (in fork master src/) is shaped for current
#     master. Two layers, two patches, both implementing the same logic.
#   - When upstream cuts a v8 release we'll either bump or retire this directory.
#
# Build:
#   docker build -t meddies/openemr:7.0.3-patched docker/meddies/
# Use (via compose override in meddies-app):
#   FROM_IMAGE=meddies/openemr:7.0.3-patched bun demo:fhir:reset

FROM openemr/openemr:7.0.3

# Replace the FHIR MedicationRequest service. The original is renamed to
# .upstream for diagnostic comparison if anything breaks.
RUN cp /var/www/localhost/htdocs/openemr/src/Services/FHIR/FhirMedicationRequestService.php \
       /var/www/localhost/htdocs/openemr/src/Services/FHIR/FhirMedicationRequestService.php.upstream

COPY FhirMedicationRequestService.patched.php \
     /var/www/localhost/htdocs/openemr/src/Services/FHIR/FhirMedicationRequestService.php

# Preserve original ownership (apache:root in the upstream image)
RUN chown 1000:0 /var/www/localhost/htdocs/openemr/src/Services/FHIR/FhirMedicationRequestService.php && \
    chmod 0400 /var/www/localhost/htdocs/openemr/src/Services/FHIR/FhirMedicationRequestService.php
