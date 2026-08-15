import { DocumentListPage } from "@/components/document/DocumentListPage";
import { receiptsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentListPage config={receiptsModule} />;
}
