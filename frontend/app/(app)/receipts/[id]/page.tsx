import { DocumentDetailPage } from "@/components/document/DocumentDetailPage";
import { receiptsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentDetailPage config={receiptsModule} />;
}
