import { JourneyProvider } from "@/lib/journey-store";
import { LandingShell } from "@/components/landing/LandingShell";

export default function Page() {
  return (
    <JourneyProvider>
      <LandingShell />
    </JourneyProvider>
  );
}
