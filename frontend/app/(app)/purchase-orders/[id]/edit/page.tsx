import { DocumentEditPage } from "@/components/document/DocumentEditPage";
import { purchaseOrdersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentEditPage config={purchaseOrdersModule} />;
}
