import { DocumentDetailPage } from "@/components/document/DocumentDetailPage";
import { purchaseOrdersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentDetailPage config={purchaseOrdersModule} />;
}
