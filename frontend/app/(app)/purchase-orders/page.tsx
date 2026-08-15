import { DocumentListPage } from "@/components/document/DocumentListPage";
import { purchaseOrdersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentListPage config={purchaseOrdersModule} />;
}
