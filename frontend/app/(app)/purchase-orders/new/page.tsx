import { DocumentNewPage } from "@/components/document/DocumentNewPage";
import { purchaseOrdersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentNewPage config={purchaseOrdersModule} />;
}
