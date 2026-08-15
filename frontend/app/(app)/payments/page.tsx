import { DocumentListPage } from "@/components/document/DocumentListPage";
import { paymentsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentListPage config={paymentsModule} />;
}
