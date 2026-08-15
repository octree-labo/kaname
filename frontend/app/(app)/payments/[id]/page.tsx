import { DocumentDetailPage } from "@/components/document/DocumentDetailPage";
import { paymentsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentDetailPage config={paymentsModule} />;
}
