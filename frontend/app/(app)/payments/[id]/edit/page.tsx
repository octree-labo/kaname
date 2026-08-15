import { DocumentEditPage } from "@/components/document/DocumentEditPage";
import { paymentsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentEditPage config={paymentsModule} />;
}
