import { DocumentDetailPage } from "@/components/document/DocumentDetailPage";
import { ordersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentDetailPage config={ordersModule} />;
}
