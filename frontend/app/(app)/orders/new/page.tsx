import { DocumentNewPage } from "@/components/document/DocumentNewPage";
import { ordersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentNewPage config={ordersModule} />;
}
