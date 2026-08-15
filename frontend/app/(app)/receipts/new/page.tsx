import { DocumentNewPage } from "@/components/document/DocumentNewPage";
import { receiptsModule } from "@/lib/documentModules";

export default function Page() {
  return <DocumentNewPage config={receiptsModule} />;
}
