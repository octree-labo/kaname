import { DocumentListPage } from "@/components/document/DocumentListPage";
import { ordersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentListPage config={ordersModule} />;
}
