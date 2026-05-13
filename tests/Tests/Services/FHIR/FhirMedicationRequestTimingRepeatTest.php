<?php

/*
 * FhirMedicationRequestTimingRepeatTest.php
 *
 * Tests that populateDosageInstruction() populates the FHIR `timing.repeat`
 * element when an HL7 timing abbreviation (BID, TID, Q6H, etc.) is present
 * in the source OpenEMR record's `interval_codes` field.
 *
 * Clinical context: downstream clinical decision support needs structured
 * frequency/period/periodUnit to compute next-dose-due times and detect
 * over-frequency prescribing. The pre-patch behavior populated only
 * `timing.code` (the abbreviation), which is human-readable but not
 * computable.
 *
 * @package openemr
 * @link    http://www.open-emr.org
 * @license https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Tests\Services\FHIR;

use Monolog\Level;
use OpenEMR\Common\Logging\SystemLogger;
use OpenEMR\FHIR\R4\FHIRDomainResource\FHIRMedicationRequest;
use OpenEMR\Services\FHIR\FhirCodeSystemConstants;
use OpenEMR\Services\FHIR\FhirMedicationRequestService;
use PHPUnit\Framework\Attributes\Test;
use PHPUnit\Framework\TestCase;
use Ramsey\Uuid\Rfc4122\UuidV4;

class FhirMedicationRequestTimingRepeatTest extends TestCase
{
    private FhirMedicationRequestService $service;

    protected function setUp(): void
    {
        $this->service = new FhirMedicationRequestService();
        $this->service->setSystemLogger(new SystemLogger(Level::Critical));
    }

    /**
     * Build a minimal valid OpenEMR record carrying a single interval code,
     * sufficient for parseOpenEMRRecord() to walk through populateDosageInstruction().
     */
    private function buildRecord(string $intervalCode): array
    {
        return [
            'uuid' => 'test-uuid-' . strtolower($intervalCode),
            'status' => 'active',
            'intent' => 'order',
            'drugcode' => [
                '197696' => [
                    'code' => '197696',
                    'description' => 'Test Medication',
                    'system' => FhirCodeSystemConstants::RXNORM,
                ],
            ],
            'drug' => 'Test Medication',
            'puuid' => UuidV4::uuid4()->toString(),
            'date_added' => '2023-01-15 10:30:00',
            'date_modified' => '2023-01-15 10:30:00',
            'drug_dosage_instructions' => 'Test dosage',
            'interval_codes' => $intervalCode,
            'interval_notes' => 'Test note',
        ];
    }

    #[Test]
    public function bidIntervalProducesTimingRepeatWithFrequencyTwoPeriodOneUnitDay(): void
    {
        $record = $this->buildRecord('BID');
        $result = $this->service->parseOpenEMRRecord($record);

        $this->assertInstanceOf(FHIRMedicationRequest::class, $result);

        $dosageInstructions = $result->getDosageInstruction();
        $this->assertNotEmpty(
            $dosageInstructions,
            'parseOpenEMRRecord should produce at least one dosageInstruction'
        );

        $timing = $dosageInstructions[0]->getTiming();
        $this->assertNotNull(
            $timing,
            'dosageInstruction[0].timing should be populated when interval_codes is present'
        );

        $repeat = $timing->getRepeat();
        $this->assertNotNull(
            $repeat,
            'dosageInstruction[0].timing.repeat must be populated for HL7 abbreviation BID '
            . '(currently only timing.code is set; this is the gap the patch closes)'
        );

        $this->assertEquals(
            2,
            $repeat->getFrequency()->getValue(),
            'BID = twice daily; expected frequency=2'
        );
        $this->assertEquals(
            1,
            $repeat->getPeriod()->getValue(),
            'BID = twice daily; expected period=1'
        );
        $this->assertEquals(
            'd',
            $repeat->getPeriodUnit()->getValue(),
            'BID = twice daily; expected periodUnit=d (day)'
        );
    }
}
