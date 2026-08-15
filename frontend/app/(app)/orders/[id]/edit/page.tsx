import { DocumentEditPage } from "@/components/document/DocumentEditPage";
import { ordersModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentEditPage config={ordersModule} />;
}
